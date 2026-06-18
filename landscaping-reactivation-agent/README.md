# Landscaping Customer Reactivation Agent

A small self-hosted Node tool for landscaping (or any local service) businesses to
win back past customers over SMS, using Twilio.

## What it does

- **`blast <campaign>`** — sends a templated SMS to every customer in `customers.csv`
  (skipping anyone who has texted STOP), and logs the results to `data/blast-log.csv`.
- **`serve`** — runs a small Express server with a `/sms` webhook for Twilio. It
  auto-replies to customer texts (YES to opt in, STOP to unsubscribe, HELP for info)
  and logs every inbound reply to `data/replies.log`.

## Setup

```bash
cd landscaping-reactivation-agent
npm install
cp .env.example .env
```

Fill in `.env` with your Twilio Account SID, Auth Token, and the phone number
you're sending from. Get these from the [Twilio Console](https://console.twilio.com).

Edit `customers.csv` with your own customer list (columns: `name,phone,last_service_date`).

## Running

```bash
# Start the reply server (defaults to port 3000)
node landscaping-reactivation-agent.js serve

# Fire a campaign blast — available campaigns: spring, summer, fall, winter
node landscaping-reactivation-agent.js blast summer
```

When self-hosting `serve`, put it behind a reverse proxy with TLS (Caddy, nginx,
Traefik, etc.) and point your Twilio phone number's "A MESSAGE COMES IN" webhook
at `https://your-domain/sms`.

## Compliance

This tool respects STOP/UNSUBSCRIBE/CANCEL replies by persisting opt-outs to
`data/opt-outs.json` and excluding those numbers from future blasts. Familiarize
yourself with TCPA and carrier messaging policies before sending marketing texts —
always honor opt-outs and only message customers who've consented to be contacted.

## Files

| File | Purpose |
|---|---|
| `landscaping-reactivation-agent.js` | CLI entry point (`serve` / `blast`) |
| `customers.csv` | Your customer list |
| `.env` | Twilio credentials and business settings (not committed) |
| `data/opt-outs.json` | Phone numbers that have opted out |
| `data/replies.log` | Log of inbound SMS replies |
| `data/blast-log.csv` | Log of outbound blast sends |
