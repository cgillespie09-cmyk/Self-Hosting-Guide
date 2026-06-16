# $1K/Week Self-Hosting Services Dashboard

A self-hosted business dashboard for selling self-hosting setup services to clients.

## What it does

Open `index.html` in any browser — no server, no install, no dependencies.

### Features
- **Dashboard** — Weekly $1,000 goal progress bar, earnings summary, pipeline stats
- **Services** — Pre-loaded with 5 sellable service packages (Docker setup, VPS config, monthly retainer, Pi-hole, backups)
- **Clients** — Track leads, active clients, and contact info
- **Invoices** — Create professional invoices, mark paid, print to PDF
- **Earnings** — Log payments, track weekly/monthly/yearly totals
- **Pitch Scripts** — 6 ready-to-copy outreach scripts (Reddit DM, email, Fiverr gig, referral ask, social media post)
- **Settings** — Your business info auto-fills on every invoice

All data is stored in browser localStorage — private and offline.

## How to hit $1,000/week

The math is simple with the pre-loaded service catalog:

| Combo | Weekly Revenue |
|---|---|
| 4× Docker Setup ($250) | $1,000 |
| 2× VPS + Proxy ($199) + 4× Backups ($125) | $898 |
| 4× active maintenance clients ($150/mo) + 2 one-time jobs | ~$1,200 |

## Quickstart

1. Open `income-toolkit/index.html` in your browser
2. Go to **Settings** and enter your name, business name, and payment info
3. Go to **Pitch Scripts** and copy the Fiverr/Upwork template — post it today
4. As clients come in, add them under **Clients** then create **Invoices**
5. Log payments under **Earnings** to track your weekly goal

## Self-hosting (optional)

To share with clients or run on a server:

```bash
# Any static file server works
npx serve income-toolkit/
# or
python3 -m http.server 8080 -d income-toolkit/
```
