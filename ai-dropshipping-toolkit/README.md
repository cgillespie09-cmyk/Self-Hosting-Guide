# DropAI — AI Dropshipping Company Toolkit

A self-hosted control center for running an AI-assisted dropshipping business: product/margin tracking, order fulfillment tracking, supplier management, an AI Studio for generating product descriptions/ad copy/customer service replies/product viability scores, ready-to-use marketing scripts, expense tracking, and a launch checklist for every external service you need to connect.

## What it does

Open `index.html` in any browser — no server, no install, no dependencies. All data is stored in your browser's `localStorage` — private and offline.

### Features

- **Dashboard** — Weekly profit goal progress, total revenue/profit/ad spend, recent orders, best-margin products
- **Products** — Catalog with supplier cost, sell price, live profit/margin calculator, shipping time, and status (testing / winning / scaling / killed)
- **Orders** — Track customer orders, fulfillment status, tracking numbers, and per-order profit
- **Suppliers** — Track sourcing partners (CJ Dropshipping, AliExpress, Zendrop, AutoDS, Spocket, etc.)
- **AI Studio** — Four AI-powered tools:
  - Product description generator
  - Ad copy generator (Facebook/Instagram, TikTok, Google Search)
  - Customer service reply generator (shipping delays, refunds, damaged items, etc.)
  - Product viability validator (margin, saturation risk, logistics risk, next steps)

  Works immediately in **template mode** with no setup. Add your own Anthropic API key in Settings to switch to **live AI mode**, where each tool calls Claude directly from your browser.
- **Marketing** — Ready-to-copy scripts: winning product checklist, organic content ideas, ad copy template, influencer outreach DM, abandoned cart email, refund de-escalation script
- **Expenses** — Log ad spend and other costs; net profit is calculated automatically from Orders minus Expenses
- **Launch Checklist** — Every external account/service you need to connect, grouped by category, with custom items supported
- **Settings** — Store name, niche, weekly profit goal, Anthropic API key, and AI model selection

## Quickstart

1. Open `ai-dropshipping-toolkit/index.html` in your browser
2. Go to **Settings** and set your store name, niche, and weekly profit goal
3. Go to **Suppliers** and add your sourcing partner, then **Products** to add your first product (the margin calculator updates live as you type cost/price)
4. Go to **AI Studio** to generate a product description and an ad for your first product (works without any API key — see "Connecting AI" below to enable live generation)
5. Use the **Marketing** tab scripts to start driving traffic
6. Log sales in **Orders** and ad spend in **Expenses** to track real profit against your weekly goal
7. Work through the **Launch Checklist** to connect the external services your business actually needs

## Connecting services (do this last)

This toolkit runs entirely offline and works without connecting anything. When you're ready to go live, the **Launch Checklist** tab walks you through every account you'll need:

| Service | Why you need it | Notes |
|---|---|---|
| Store platform (Shopify, WooCommerce, etc.) | Your actual storefront where customers buy | Not included in this toolkit — this dashboard is your back-office command center |
| Domain registrar | A custom domain for your store | Any registrar (Namecheap, Google Domains, etc.) |
| Payment processor (Stripe / PayPal Business) | Accept real payments | Required by virtually every store platform |
| Supplier account (CJ Dropshipping, Zendrop, AutoDS, Spocket, AliExpress) | Source and fulfill products | Pick one based on shipping speed and niche fit |
| Meta Business Manager / TikTok Ads | Paid traffic + tracking pixels | Optional to start — organic content works too |
| **Anthropic API key** | Enables live AI generation in **AI Studio** | Optional — the toolkit works in template mode without it. Get a key at [console.anthropic.com](https://console.anthropic.com), paste it into **Settings → Anthropic API Key**. It's stored only in your browser and sent directly to Anthropic's API — never to any third-party server. |

## Self-hosting (optional)

To share with a team or run on a server:

```bash
# Any static file server works
npx serve ai-dropshipping-toolkit/
# or
python3 -m http.server 8080 -d ai-dropshipping-toolkit/
```

## Important notes

- This is a business **operations toolkit**, not a hosted storefront — you still need a store platform (Shopify/WooCommerce) for customers to actually buy from.
- Nothing here automates real money movement, ad spend, or supplier orders — those require the actual third-party accounts listed above. The toolkit's job is to track margins, generate content, and keep you organized while you run the business.
- Dropshipping profit is not guaranteed. Treat the weekly goal, margin calculator, and product validator as planning aids, not promises.
