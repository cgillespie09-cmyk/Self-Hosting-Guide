#!/usr/bin/env node
'use strict';

require('dotenv').config({ path: require('path').join(__dirname, '.env') });

const fs = require('fs');
const path = require('path');
const express = require('express');
const twilio = require('twilio');
const { parse } = require('csv-parse/sync');

const DATA_DIR = path.join(__dirname, 'data');
const CUSTOMERS_CSV = path.join(__dirname, 'customers.csv');
const OPT_OUT_FILE = path.join(DATA_DIR, 'opt-outs.json');
const REPLIES_LOG = path.join(DATA_DIR, 'replies.log');
const BLAST_LOG = path.join(DATA_DIR, 'blast-log.csv');

const BUSINESS_NAME = process.env.BUSINESS_NAME || 'Your Landscaping Co';
const BOOKING_URL = process.env.BOOKING_URL || '';
const PORT = process.env.PORT || 3000;
const BLAST_DELAY_MS = Number(process.env.BLAST_DELAY_MS) || 1100;

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
    lastServiceDate: row.last_service_date,
  }));
}

function renderTemplate(template, customer) {
  return template
    .replace(/{{\s*name\s*}}/g, customer.name)
    .replace(/{{\s*business\s*}}/g, BUSINESS_NAME);
}

function getTwilioClient() {
  const accountSid = process.env.TWILIO_ACCOUNT_SID;
  const authToken = process.env.TWILIO_AUTH_TOKEN;
  if (!accountSid || !authToken) {
    throw new Error('TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set (see .env.example).');
  }
  return twilio(accountSid, authToken);
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
    console.error(`Unknown campaign "${campaignName}". Available: ${Object.keys(CAMPAIGNS).join(', ')}`);
    process.exitCode = 1;
    return;
  }

  const fromNumber = process.env.TWILIO_FROM_NUMBER;
  if (!fromNumber) {
    console.error('TWILIO_FROM_NUMBER must be set (see .env.example).');
    process.exitCode = 1;
    return;
  }

  const client = getTwilioClient();
  const optOuts = loadOptOuts();
  const customers = loadCustomers().filter((c) => !optOuts.has(c.phone));

  console.log(`Sending "${campaignName}" campaign to ${customers.length} customer(s)...`);

  const logRows = [];
  let sent = 0;
  let failed = 0;

  for (const customer of customers) {
    const body = renderTemplate(template, customer);
    const timestamp = new Date().toISOString();
    try {
      await client.messages.create({ to: customer.phone, from: fromNumber, body });
      sent += 1;
      logRows.push([timestamp, campaignName, customer.phone, customer.name, 'sent', '']);
      console.log(`  sent -> ${customer.name} (${customer.phone})`);
    } catch (err) {
      failed += 1;
      logRows.push([timestamp, campaignName, customer.phone, customer.name, 'failed', err.message.replace(/,/g, ';')]);
      console.error(`  failed -> ${customer.name} (${customer.phone}): ${err.message}`);
    }
    await new Promise((resolve) => setTimeout(resolve, BLAST_DELAY_MS));
  }

  appendBlastLog(logRows);
  console.log(`Done. Sent: ${sent}, Failed: ${failed}, Skipped (opted out): ${optOuts.size}`);
}

function buildReply(body) {
  const text = body.trim().toUpperCase();

  if (['STOP', 'STOPALL', 'UNSUBSCRIBE', 'CANCEL', 'END', 'QUIT'].includes(text)) {
    return { intent: 'opt-out', reply: `You're unsubscribed from ${BUSINESS_NAME} texts and won't receive further messages. Reply START to resubscribe.` };
  }

  if (['START', 'YES', 'Y'].includes(text)) {
    const booking = BOOKING_URL ? ` Book a time here: ${BOOKING_URL}` : " We'll text you shortly to set up a time.";
    return { intent: 'opt-in', reply: `Great! Thanks for getting back to us.${booking}` };
  }

  if (text === 'HELP') {
    return { intent: 'help', reply: `${BUSINESS_NAME}: Reply YES to book a visit, STOP to unsubscribe.` };
  }

  return { intent: 'other', reply: `Thanks for the reply! Someone from ${BUSINESS_NAME} will follow up shortly.` };
}

function logReply(entry) {
  ensureDataDir();
  fs.appendFileSync(REPLIES_LOG, `${JSON.stringify(entry)}\n`);
}

function startServer() {
  const app = express();
  app.set('trust proxy', true); // honor X-Forwarded-* when run behind a reverse proxy
  app.use(express.urlencoded({ extended: false }));

  const authToken = process.env.TWILIO_AUTH_TOKEN;
  const validateTwilioRequest = authToken
    ? twilio.webhook({ validate: true })
    : (req, res, next) => next();

  if (!authToken) {
    console.warn('TWILIO_AUTH_TOKEN not set — incoming webhook signature validation is disabled.');
  }

  app.get('/health', (req, res) => res.json({ ok: true }));

  app.post('/sms', validateTwilioRequest, (req, res) => {
    const from = req.body.From;
    const body = req.body.Body || '';
    const { intent, reply } = buildReply(body);

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

  app.listen(PORT, () => {
    console.log(`Reply server listening on port ${PORT}. Point your Twilio webhook at POST /sms.`);
  });
}

function printUsage() {
  console.log(`Usage:
  node landscaping-reactivation-agent.js serve          Start the reply server (webhook: POST /sms)
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
    await runBlast(arg);
  } else {
    printUsage();
    process.exitCode = command ? 1 : 0;
  }
}

main();
