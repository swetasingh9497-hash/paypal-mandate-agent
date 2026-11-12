# Budgie

> An AI shopping agent that buys on your behalf, but only inside the spending rules you set. Payments run through PayPal.

*(Formerly "Mandate". The repository name `paypal-mandate-agent` is kept from that earlier name.)*

## The problem

AI agents can already search and shop, but people don't trust them with their money. Handing an agent your payment details is all-or-nothing: either it can spend freely, or it can't act at all.

## Our solution

You give Budgie a **mandate** in plain language, for example:

> "Mouse under $50, auto-buy under $30."

Budgie turns this into strict rules, finds matching products, and checks every candidate against those rules. Each product gets one of three decisions, with reasons:

- **`auto_pay`**: within your auto-approve limit (the buyer still approves on PayPal)
- **`needs_approval`**: passes the rules but needs your explicit confirmation, or has missing data (e.g. no rating or delivery estimate)
- **`reject`**: breaks a rule, and Budgie tells you exactly why

**Core principle: the LLM proposes, deterministic code decides, PayPal executes.** The LLM only (1) translates your request into a structured mandate and (2) ranks and explains products that already passed the rules. It cannot change prices, override a rejection or authorize a payment.

## How it works

```
Mandate (text)
   -> Gemini parser -> validated Mandate (Pydantic) + budget grounding check
   -> Product search (Channel3, mock fallback)
   -> Rules engine (deterministic Python) -> auto_pay | needs_approval | reject
   -> Gemini ranks and explains the passing products
   -> PayPal Sandbox order -> buyer approval -> verified capture
```

## Why PayPal and AI both matter

- **AI (Google Gemini):** parses natural-language requests into structured mandates, and ranks and explains products that already passed the rules.
- **PayPal:** the Orders API (Sandbox) creates the order, the buyer approves it on PayPal, and the backend verifies the capture (status, capture ID, amount, currency) before saving anything.

Without AI there is no agent. Without PayPal the agent cannot safely complete a purchase.

## Features

- Natural-language mandate -> validated structured rules
- Budget grounding check: budget values must actually appear in the user's request
- Deterministic rules engine (budget, rating, delivery, monthly spending cap)
- Missing data (rating, delivery) routes to human approval instead of auto-rejecting
- Approval flow before payment, with PayPal buyer approval
- Spending dashboard with monthly limits and recent orders
- Audit events for pipeline decisions and payment operations
- Fallback product ranking and mock product search when external services are unavailable

## Safety design

- The rules engine is plain code with unit tests, not an LLM.
- Product titles and descriptions are treated as untrusted input (prompt injection cannot change the rules).
- The server uses the price stored during the shopping run, never a price sent by the browser.
- Authenticated access with order ownership checks.
- Atomic order replacement: switching products supersedes the old order in one database transaction, and superseded orders cannot be captured.
- Secrets live in `.env` and are never committed.

## Tech stack

Python, FastAPI, Pydantic, SQLite, httpx, Google Gemini, Channel3, PayPal Orders API (Sandbox), React, TypeScript, Tailwind CSS, pytest, Vitest

## Getting started

**Prerequisites:** Python 3.11+, Node.js (for the frontend), a PayPal Developer account.

```bash
git clone https://github.com/swetasingh9497-hash/paypal-mandate-agent.git
cd paypal-mandate-agent
python -m venv .venv
# Windows: .venv\Scripts\activate   |  Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # Windows: copy .env.example .env
```

Fill in `.env` (see `.env.example` for the exact variable names):

```
PAYPAL_CLIENT_ID=
PAYPAL_SECRET=
GEMINI_API_KEY=
CHANNEL3_API_KEY=
LLM_MODEL=gemini-3.5-flash-lite
```

Run the backend:

```bash
uvicorn app.main:app --reload
```

Run the tests:

```bash
pytest -q
```

Frontend: see the frontend folder / README for `npm install` and `npm run dev`.

> **Note:** This project uses the PayPal **Sandbox**. No real money moves. To test checkout, use a Sandbox *Personal* (buyer) account created with country set to United States.

## Demo

- Demo video: https://youtu.be/m7ZWxdQlKno
- Devpost: https://devpost.com/software/budgie-elprz6

## Team

- **Sweta Singh**: backend, Gemini integration, Channel3 search, PayPal Sandbox payment flow
- **Vaibhav Vishwakarma**: frontend, spending dashboard, testing and integration fixes

## Limitations and roadmap

- All payments use PayPal Sandbox. No real money is transferred.
- Channel3 does not give reliable delivery estimates or ratings for every listing, so some items need manual approval.
- The spending dashboard may mix seeded sample data with real Sandbox orders (sample data is labelled).
- Auth is a prototype mechanism, not a production identity provider.
- Next: PayPal OAuth, per-category budgets and recurring purchases, better delivery/rating data, persistent database and stronger rate limiting, and an independent security review before any real-money use.

## License

MIT
