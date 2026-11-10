# Mandate Agent

> An AI shopping agent that buys on your behalf, but only inside the spending rules you set. Payments run through PayPal.

## The problem

AI agents can already search and shop, but people don't trust them with their money. Handing an agent your payment details is all-or-nothing: either it can spend freely, or it can't act at all.

## Our solution

You give the agent a **mandate** in plain language, for example:

> "A desk lamp under $60, rated 4 stars or above, delivered within a week."

The agent turns this into strict rules, finds matching products, and checks every candidate against those rules. Depending on the result it will:

- **Auto-pay** if the item is within your auto-approve limit,
- **Ask for your approval** if it passes the rules but costs more than that limit,
- **Reject** the item if it breaks any rule, and tell you exactly why.

**The key design idea: the LLM never decides whether money moves.** The LLM only (1) translates your request into structured rules and (2) ranks and explains the products that already passed. The payment decision is made by plain, tested Python code.

## How it works

```
Mandate (text)
   -> LLM parser -> validated Mandate (JSON)
   -> Product search
   -> Rules engine (deterministic Python) -> auto_pay | needs_approval | reject
   -> LLM ranks and explains the passing products
   -> PayPal order -> buyer approval -> capture
```

<!-- TODO: add an architecture diagram image here -->

## Why PayPal and AI both matter

- **AI:** <what the LLM does in your build, e.g. mandate parsing, ranking, explanations>
- **PayPal:** <what you use, e.g. Orders API to create and capture payments, buyer approval flow>

Neither works alone: without AI there is no agent, and without PayPal the agent cannot safely complete a purchase.

## Features

- Natural-language mandate -> validated structured rules
- Deterministic rules engine (budget, rating, delivery time, blocked merchants, currency)
- Safe defaults: missing data means reject
- Human approval flow for purchases above the auto-approve limit
- Full audit trail: why each product was chosen or rejected
- <add only what is actually built>

## Safety design

- The rules engine is plain code with unit tests, not an LLM.
- Product titles and descriptions are treated as untrusted text. <describe your prompt-injection defence once built>
- Missing data (no rating, no delivery estimate) is rejected, never assumed fine.
- Secrets live in `.env` and are never committed.

## Tech stack

Python, FastAPI, Pydantic, httpx, <LLM provider>, <product data API>, React, PayPal Orders API (Sandbox), <deployment platform>

## Getting started

**Prerequisites:** Python 3.11+, Node.js (for the frontend), a PayPal Developer account.

```bash
git clone https://github.com/<your-username>/mandate-agent.git
cd mandate-agent
python -m venv .venv
# Windows: .venv\Scripts\activate   |  Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # Windows: copy .env.example .env
```

Fill in `.env`:

```
PAYPAL_CLIENT_ID=
PAYPAL_SECRET=
ANTHROPIC_API_KEY=
CHANNEL3_API_KEY=
LLM_MODEL=
```

Run the backend:

```bash
uvicorn app.main:app --reload
```

Run the tests:

```bash
pytest -q
```

Frontend: <add steps once the frontend exists>

> **Note:** This project uses the PayPal **Sandbox**. No real money moves. To test checkout, use a Sandbox *Personal* (buyer) account created with country set to United States.

## Demo

- Live app: <link>
- Demo video: <link>

## Team

- <Your name> - <role, e.g. agent core and AI>
- <Teammate name> - <role, e.g. frontend and payment flow>

## Limitations and roadmap

- Currently Sandbox only
- <honest list of what is missing or simplified>
- Next: <2 or 3 realistic ideas>

## License

MIT