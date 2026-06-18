# Landscaping Customer Reactivation Agent

A small self-hosted Node tool for landscaping (or any local service) businesses to
win back past customers over SMS, using Twilio — with a web dashboard so the
business owner can plug in their info without touching code.

## What it does

- **Web dashboard** — configure your business name, booking link, and Twilio
  credentials; manage your customer list; fire campaign blasts; and review
  replies/opt-outs, all from the browser.
- **`blast <campaign>`** — sends a templated SMS to every customer in `customers.csv`
  (skipping anyone who has texted STOP), and logs the results to `data/blast-log.csv`.
- **`serve`** — runs an Express server with a `/sms` webhook for Twilio. It
  auto-replies to customer texts (YES to opt in, STOP to unsubscribe, HELP for info),
  logs every inbound reply to `data/replies.log`, and serves the dashboard.

## Setup

```bash
cd landscaping-reactivation-agent
npm install
cp .env.example .env
```

At minimum, set `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` in `.env` — these
protect the web dashboard. Everything else (Twilio SID/token/number, business
name, booking URL) can be filled in later from the dashboard's **Settings** tab
instead of editing `.env` by hand; values entered there are saved to
`data/settings.json` and take effect immediately.

## Running

```bash
node landscaping-reactivation-agent.js serve
```

Then open `http://localhost:3000` (or your server's address) in a browser, log
in with your dashboard username/password, and use the tabs:

- **Settings** — business name, booking URL, Twilio Account SID/Auth Token/From Number
- **Customers** — add customers one at a time, remove them, or paste a CSV to
  replace the whole list
- **Campaigns** — preview the seasonal templates (spring/summer/fall/winter) and
  send a blast with one click
- **Activity** — opted-out numbers (with a resubscribe button), recent inbound
  replies, and blast send history

The same actions are available from the command line:

```bash
node landscaping-reactivation-agent.js blast summer
```

When self-hosting `serve`, put it behind a reverse proxy with TLS (Caddy, nginx,
Traefik, etc.) and point your Twilio phone number's "A MESSAGE COMES IN" webhook
at `https://your-domain/sms`. The dashboard itself should only be reachable over
HTTPS or a trusted network, since it can display your Twilio credentials to
anyone who logs in.

## Compliance

This tool respects STOP/UNSUBSCRIBE/CANCEL replies by persisting opt-outs to
`data/opt-outs.json` and excluding those numbers from future blasts. Familiarize
yourself with TCPA and carrier messaging policies before sending marketing texts —
always honor opt-outs and only message customers who've consented to be contacted.

## Files

| File | Purpose |
|---|---|
| `landscaping-reactivation-agent.js` | CLI entry point (`serve` / `blast`) + API |
| `config.js` | Loads/saves dashboard settings (`data/settings.json`) |
| `public/` | Web dashboard (static HTML/CSS/JS) |
| `customers.csv` | Your customer list |
| `.env` | Dashboard login and initial defaults (not committed) |
| `data/settings.json` | Business/Twilio settings saved from the dashboard (not committed) |
| `data/opt-outs.json` | Phone numbers that have opted out |
| `data/replies.log` | Log of inbound SMS replies |
| `data/blast-log.csv` | Log of outbound blast sends |
