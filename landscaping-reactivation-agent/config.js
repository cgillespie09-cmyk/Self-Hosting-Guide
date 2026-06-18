'use strict';

const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, 'data');
const SETTINGS_FILE = path.join(DATA_DIR, 'settings.json');

const DEFAULTS = {
  businessName: process.env.BUSINESS_NAME || 'Your Landscaping Co',
  bookingUrl: process.env.BOOKING_URL || '',
  twilioAccountSid: process.env.TWILIO_ACCOUNT_SID || '',
  twilioAuthToken: process.env.TWILIO_AUTH_TOKEN || '',
  twilioFromNumber: process.env.TWILIO_FROM_NUMBER || '',
  blastDelayMs: Number(process.env.BLAST_DELAY_MS) || 1100,
};

// Settings entered through the dashboard are persisted to disk so they
// survive restarts without requiring the owner to edit .env by hand.
let cache = null;

function load() {
  if (cache) return cache;
  let stored = {};
  try {
    stored = JSON.parse(fs.readFileSync(SETTINGS_FILE, 'utf8'));
  } catch {
    stored = {};
  }
  cache = { ...DEFAULTS, ...stored };
  return cache;
}

function save(partial) {
  const next = { ...load(), ...partial };
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(SETTINGS_FILE, JSON.stringify(next, null, 2));
  cache = next;
  return next;
}

module.exports = { load, save };
