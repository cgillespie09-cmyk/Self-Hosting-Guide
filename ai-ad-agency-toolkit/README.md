# AdAI — AI-Automated Ad Agency for Local Businesses

A self-contained business dashboard for running an agency that uses AI automation
to create, launch, and manage ads (Google, Meta/Instagram, Google Business Profile)
for local businesses — restaurants, dentists, salons, gyms, contractors, auto shops, etc.

## What it does

Open `index.html` in any browser — no server, no install, no dependencies.

### Features
- **Dashboard** — Weekly income goal progress bar, earnings summary, pipeline stats
- **Services** — Pre-loaded with 5 sellable ad packages (AI launch package, monthly
  management retainer, AI creative pack, local SEO + ads bundle, reporting dashboard)
- **Clients** — Track leads, active clients, and contact info
- **Invoices** — Create professional invoices, mark paid, print to PDF
- **Earnings** — Log payments, track weekly/monthly/yearly totals
- **Pitch Scripts** — 6 ready-to-copy outreach scripts aimed at local businesses
- **Settings** — Your business info auto-fills on every invoice

All data is stored in browser localStorage — private and offline.

## The business model

You are the "AI ad department" local businesses don't have time to build themselves.
For a setup fee plus a monthly retainer, you:

1. Set up and launch ad campaigns (Google Search/Local, Meta/Instagram, Google
   Business Profile) for the client
2. Use AI tools to do the heavy lifting so one person can service many clients:
   - **Ad copy & headlines** — ChatGPT/Claude to generate and A/B test ad copy
   - **Creative assets** — AI image/video tools (Canva AI, Midjourney, Sora/Runway)
     for ad graphics and short video ads
   - **Campaign automation** — Zapier/Make/n8n to sync leads from ad forms into a
     CRM or spreadsheet and trigger follow-up emails/texts automatically
   - **Targeting & bidding** — native Google Ads / Meta Ads Manager automated
     bidding, layered with AI-assisted audience research
   - **Reporting** — AI-generated weekly performance summaries (Looker Studio /
     Google Sheets + a script or LLM prompt that turns raw numbers into a plain
     English client update)
3. Charge a one-time launch fee + a monthly management retainer (the recurring
   revenue is what makes this scale)

## How to hit $1,000/week

| Combo | Weekly Revenue |
|---|---|
| 2× AI Ad Launch Package ($399) + 1× monthly retainer billed this week ($400) | ~$1,200 |
| 4× active monthly retainers ($400/mo, billed monthly) ≈ $1,600/mo | ~$400/wk recurring, stack with launches |
| 1× Local SEO + Ads Bundle ($249) + 2× AI Creative Pack ($149) + 1× retainer ($400) | ~$947 |

Recurring retainers are the goal — a handful of monthly clients gives you a
baseline income before you even sell a new project that week.

## Quickstart

1. Open `ai-ad-agency-toolkit/index.html` in your browser
2. Go to **Settings** and enter your name, business name, and payment info
3. Go to **Pitch Scripts** and copy a template — send it to 10 local businesses today
4. As clients come in, add them under **Clients** then create **Invoices**
5. Log payments under **Earnings** to track your weekly goal

## Tooling you'll actually use to deliver the service

- **Ad platforms**: Google Ads, Meta Ads Manager, Google Business Profile
- **AI copy/creative**: ChatGPT or Claude for copy, Canva (AI features) or
  Midjourney for images
- **Automation**: Zapier, Make, or self-hosted n8n to connect lead forms →
  spreadsheet/CRM → follow-up
- **Reporting**: Google Sheets or Looker Studio, summarized into a client-friendly
  report (an LLM prompt works well for turning a CSV export into a plain-English
  weekly update)

## Self-hosting (optional)

To share with clients or run on a server:

```bash
# Any static file server works
npx serve ai-ad-agency-toolkit/
# or
python3 -m http.server 8080 -d ai-ad-agency-toolkit/
```
