#!/usr/bin/env node
'use strict';

require('dotenv').config({ path: require('path').join(__dirname, '.env') });

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const express = require('express');
const twilio = require('twilio');
const { parse } = require('csv-parse/sync');
const config = require('./config');

const DATA_DIR = path.join(__dirname, 'data');
const PUBLIC_DIR = path.join(__dirname, 'public');
const CUSTOMERS_CSV = path.join(__dirname, 'customers.csv');
const OPT_OUT_FILE = path.join(DATA_DIR, 'opt-outs.json');
const REPLIES_LOG = path.join(DATA_DIR, 'replies.log');
const BLAST_LOG = path.join(DATA_DIR, 'blast-log.csv');

const PORT = process.env.PORT || 3000;

const CAMPAIGNS = {
  spring: 'Hi {{name}}, it\'s {{business}} — spring clean-up season is here! Reply YES to grab a spot, or STOP to opt out.',
  summer: 'Hi {{name}}, {{business}} here. Your lawn is probably growing fast this summer — want us back out for a trim? Reply YES to book, or STOP to opt out.',
  fall: 'Hi {{name}}, {{business}} here — fall cleanup season is here. Reply YES for a quote, or STOP to unsubscribe.',
  winter: 'Hi {{name}}, {{business}} here. Ready for winter prep? Reply YES and we\'ll reach out, or STOP to opt out.',
};

function ensureDataDir() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

function loadOptOuts() {
  try {
    return new Set(JSON.parse(fs.readFileSync(OPT_OUT_FILE, 'utf8')));
  } catch {
    return new Set();
  }
}

function saveOptOuts(optOuts) {
  ensureDataDir();
  fs.writeFileSync(OPT_OUT_FILE, JSON.stringify([...optOuts], null, 2));
}

function normalizePhone(raw) {
  const digits = raw.replace(/[^\d+]/g, '');
  if (digits.startsWith('+')) return digits;
  if (digits.length === 10) return `+1${digits}`;
  if (digits.length === 11 && digits.startsWith('1')) return `+${digits}`;
  return `+${digits}`;
}

function loadCustomers() {
  const content = fs.readFileSync(CUSTOMERS_CSV, 'utf8');
  const rows = parse(content, { columns: true, skip_empty_lines: true, trim: true });
  return rows.map((row) => ({
    name: row.name,
    phone: normalizePhone(row.phone),
    lastServiceDate: row.last_service_date || '',
  }));
}

function csvEscape(value) {
  const str = String(value ?? '');
  return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
}

function writeCustomers(customers) {
  const lines = ['name,phone,last_service_date'];
  for (const c of customers) {
    lines.push([csvEscape(c.name), csvEscape(c.phone), csvEscape(c.lastServiceDate)].join(','));
  }
  fs.writeFileSync(CUSTOMERS_CSV, `${lines.join('\n')}\n`);
}

function renderTemplate(template, customer, businessName) {
  return template
    .replace(/{{\s*name\s*}}/g, customer.name)
    .replace(/{{\s*business\s*}}/g, businessName);
}

function appendBlastLog(rows) {
  ensureDataDir();
  const isNew = !fs.existsSync(BLAST_LOG);
  const stream = fs.createWriteStream(BLAST_LOG, { flags: 'a' });
  if (isNew) stream.write('timestamp,campaign,phone,name,status,error\n');
  for (const row of rows) {
    stream.write(`${row.join(',')}\n`);
  }
  stream.end();
}

async function runBlast(campaignName) {
  const template = CAMPAIGNS[campaignName];
  if (!template) {
    throw new Error(`Unknown campaign "${campaignName}". Available: ${Object.keys(CAMPAIGNS).join(', ')}`);
  }

  const settings = config.load();
  if (!settings.twilioAccountSid || !settings.twilioAuthToken) {
    throw new Error('Twilio Account SID and Auth Token are not set. Configure them in Settings.');
  }
  if (!settings.twilioFromNumber) {
    throw new Error('Twilio "from" number is not set. Configure it in Settings.');
  }

  const client = twilio(settings.twilioAccountSid, settings.twilioAuthToken);
  const optOuts = loadOptOuts();
  const customers = loadCustomers().filter((c) => !optOuts.has(c.phone));

  const logRows = [];
  let sent = 0;
  let failed = 0;

  for (const customer of customers) {
    const body = renderTemplate(template, customer, settings.businessName);
    const timestamp = new Date().toISOString();
    try {
      await client.messages.create({ to: customer.phone, from: settings.twilioFromNumber, body });
      sent += 1;
      logRows.push([timestamp, campaignName, customer.phone, customer.name, 'sent', '']);
    } catch (err) {
      failed += 1;
      logRows.push([timestamp, campaignName, customer.phone, customer.name, 'failed', err.message.replace(/,/g, ';')]);
    }
    await new Promise((resolve) => setTimeout(resolve, settings.blastDelayMs));
  }

  appendBlastLog(logRows);
  return { campaign: campaignName, sent, failed, skipped: optOuts.size, total: customers.length };
}

function buildReply(body, settings) {
  const text = body.trim().toUpperCase();

  if (['STOP', 'STOPALL', 'UNSUBSCRIBE', 'CANCEL', 'END', 'QUIT'].includes(text)) {
    return { intent: 'opt-out', reply: `You're unsubscribed from ${settings.businessName} texts and won't receive further messages. Reply START to resubscribe.` };
  }

  if (['START', 'YES', 'Y'].includes(text)) {
    const booking = settings.bookingUrl ? ` Book a time here: ${settings.bookingUrl}` : " We'll text you shortly to set up a time.";
    return { intent: 'opt-in', reply: `Great! Thanks for getting back to us.${booking}` };
  }

  if (text === 'HELP') {
    return { intent: 'help', reply: `${settings.businessName}: Reply YES to book a visit, STOP to unsubscribe.` };
  }

  return { intent: 'other', reply: `Thanks for the reply! Someone from ${settings.businessName} will follow up shortly.` };
}

function logReply(entry) {
  ensureDataDir();
  fs.appendFileSync(REPLIES_LOG, `${JSON.stringify(entry)}\n`);
}

function validateTwilioRequest(req, res, next) {
  const settings = config.load();
  if (!settings.twilioAuthToken) return next();

  const signature = req.headers['x-twilio-signature'];
  const url = `${req.protocol}://${req.get('host')}${req.originalUrl}`;
  const isValid = twilio.validateRequest(settings.twilioAuthToken, signature, url, req.body);
  if (isValid) return next();
  res.status(403).send('Invalid Twilio signature');
}

function safeCompare(a, b) {
  const bufA = Buffer.from(String(a));
  const bufB = Buffer.from(String(b));
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}

function requireDashboardAuth(req, res, next) {
  const username = process.env.DASHBOARD_USERNAME;
  const password = process.env.DASHBOARD_PASSWORD;
  if (!username || !password) {
    return res.status(503).send('Dashboard disabled: set DASHBOARD_USERNAME and DASHBOARD_PASSWORD in .env to enable it.');
  }

  const header = req.headers.authorization || '';
  const [scheme, encoded] = header.split(' ');
  if (scheme === 'Basic' && encoded) {
    const decoded = Buffer.from(encoded, 'base64').toString('utf8');
    const sepIndex = decoded.indexOf(':');
    const user = decoded.slice(0, sepIndex);
    const pass = decoded.slice(sepIndex + 1);
    if (safeCompare(user, username) && safeCompare(pass, password)) {
      return next();
    }
  }

  res.set('WWW-Authenticate', 'Basic realm="Landscaping Dashboard"');
  res.status(401).send('Authentication required.');
}

function buildApiRouter() {
  const router = express.Router();

  router.get('/settings', (req, res) => {
    res.json(config.load());
  });

  router.post('/settings', (req, res) => {
    const allowed = ['businessName', 'bookingUrl', 'twilioAccountSid', 'twilioAuthToken', 'twilioFromNumber', 'blastDelayMs'];
    const partial = {};
    for (const key of allowed) {
      if (req.body[key] === undefined) continue;
      partial[key] = key === 'blastDelayMs' ? Number(req.body[key]) || 1100 : req.body[key];
    }
    res.json(config.save(partial));
  });

  router.get('/customers', (req, res) => {
    res.json(loadCustomers());
  });

  router.post('/customers', (req, res) => {
    const { name, phone, lastServiceDate } = req.body;
    if (!name || !phone) {
      return res.status(400).json({ error: 'name and phone are required' });
    }
    const customers = loadCustomers();
    customers.push({ name, phone: normalizePhone(phone), lastServiceDate: lastServiceDate || '' });
    writeCustomers(customers);
    res.status(201).json(customers);
  });

  router.delete('/customers/:phone', (req, res) => {
    const target = normalizePhone(req.params.phone);
    writeCustomers(loadCustomers().filter((c) => c.phone !== target));
    res.json(loadCustomers());
  });

  router.post('/customers/import', (req, res) => {
    const { csv } = req.body;
    if (!csv) return res.status(400).json({ error: 'csv text is required' });
    try {
      parse(csv, { columns: true, skip_empty_lines: true, trim: true });
    } catch (err) {
      return res.status(400).json({ error: `Invalid CSV: ${err.message}` });
    }
    fs.writeFileSync(CUSTOMERS_CSV, `${csv.trim()}\n`);
    res.json(loadCustomers());
  });

  router.get('/campaigns', (req, res) => {
    res.json(CAMPAIGNS);
  });

  router.post('/campaigns/:name/blast', async (req, res) => {
    try {
      const result = await runBlast(req.params.name);
      res.json(result);
    } catch (err) {
      res.status(400).json({ error: err.message });
    }
  });

  router.get('/opt-outs', (req, res) => {
    res.json([...loadOptOuts()]);
  });

  router.delete('/opt-outs/:phone', (req, res) => {
    const optOuts = loadOptOuts();
    optOuts.delete(normalizePhone(req.params.phone));
    saveOptOuts(optOuts);
    res.json([...optOuts]);
  });

  router.get('/replies', (req, res) => {
    try {
      const lines = fs.readFileSync(REPLIES_LOG, 'utf8').trim().split('\n').filter(Boolean);
      res.json(lines.slice(-200).reverse().map((line) => JSON.parse(line)));
    } catch {
      res.json([]);
    }
  });

  router.get('/blast-log', (req, res) => {
    try {
      const content = fs.readFileSync(BLAST_LOG, 'utf8').trim();
      res.json(parse(content, { columns: true, skip_empty_lines: true }).reverse());
    } catch {
      res.json([]);
    }
  });

  return router;
}

function startServer() {
  const app = express();
  app.set('trust proxy', true); // honor X-Forwarded-* when run behind a reverse proxy
  app.use(express.urlencoded({ extended: false }));
  app.use(express.json());

  app.get('/health', (req, res) => res.json({ ok: true }));

  app.post('/sms', validateTwilioRequest, (req, res) => {
    const settings = config.load();
    const from = req.body.From;
    const body = req.body.Body || '';
    const { intent, reply } = buildReply(body, settings);

    if (intent === 'opt-out' && from) {
      const optOuts = loadOptOuts();
      optOuts.add(normalizePhone(from));
      saveOptOuts(optOuts);
    }
    if (intent === 'opt-in' && from) {
      const optOuts = loadOptOuts();
      optOuts.delete(normalizePhone(from));
      saveOptOuts(optOuts);
    }

    logReply({ timestamp: new Date().toISOString(), from, body, intent });

    const twiml = new twilio.twiml.MessagingResponse();
    twiml.message(reply);
    res.type('text/xml').send(twiml.toString());
  });

  if (!process.env.DASHBOARD_USERNAME || !process.env.DASHBOARD_PASSWORD) {
    console.warn('DASHBOARD_USERNAME/DASHBOARD_PASSWORD not set — the web dashboard is disabled. The /sms webhook still works.');
  }

  // Everything below requires dashboard auth; /sms and /health stay public for Twilio/health checks.
  app.use(requireDashboardAuth);
  app.use('/api', buildApiRouter());
  app.use(express.static(PUBLIC_DIR));

  app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}.`);
    console.log(`  Twilio webhook: POST /sms`);
    console.log(`  Dashboard:      GET  /`);
  });
}

function printUsage() {
  console.log(`Usage:
  node landscaping-reactivation-agent.js serve          Start the reply server + web dashboard
  node landscaping-reactivation-agent.js blast <name>    Send a campaign blast from customers.csv

Available campaigns: ${Object.keys(CAMPAIGNS).join(', ')}`);
}

async function main() {
  const [command, arg] = process.argv.slice(2);

  if (command === 'serve') {
    startServer();
  } else if (command === 'blast') {
    if (!arg) {
      printUsage();
      process.exitCode = 1;
      return;
    }
    try {
      const result = await runBlast(arg);
      console.log(`Done. Sent: ${result.sent}, Failed: ${result.failed}, Skipped (opted out): ${result.skipped}`);
    } catch (err) {
      console.error(err.message);
      process.exitCode = 1;
    }
  } else {
    printUsage();
    process.exitCode = command ? 1 : 0;
  }
}

main();
