from dotenv import load_dotenv
load_dotenv()

import os
import time
import logging
from collections import defaultdict, deque
import httpx
from fastapi import FastAPI, HTTPException, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from .paypal import capture_order, create_order
from .pipeline import run_pipeline, ORDERS
from .db import get_order, capture_order_db, get_spending_data, get_run, insert_order, insert_run, get_monthly_spent, MONTHLY_CAP

# Environment configuration with safe defaults
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

# Startup logging (no secrets)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting Mandate API")
logger.info("CORS allowed origins: %s", CORS_ORIGINS)
logger.info("Frontend URL: %s", FRONTEND_URL)
logger.info("Backend URL: %s", BACKEND_URL)

# --- simple per-IP rate limit (memory mein, restart par reset hota hai) ---
_hits = defaultdict(deque)

def rate_limit(request: Request, limit: int = 5, window: int = 60):
    # Hosting platform ke peeche asli IP X-Forwarded-For mein aata hai
    fwd = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    ip = fwd or (request.client.host if request.client else "unknown")
    q = _hits[ip]
    now = time.time()
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")
    q.append(now)

app = FastAPI(title="Mandate")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunRequest(BaseModel):
    text: str = Field(min_length=3, max_length=500)
    user_email: str = "demo@mandate.app"

class SelectRequest(BaseModel):
    product_id: str
    user_email: str

@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/run")
async def run(req: RunRequest, request: Request):
    rate_limit(request)
    try:
        return await run_pipeline(req.text, req.user_email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"PayPal error: {e.response.text}")
    except Exception as e:
        logging.exception("Unhandled error in /api/run")
        raise HTTPException(status_code=502, detail=f"{type(e).__name__}: {e}")

@app.post("/api/mock/run")
async def run_mock(req: RunRequest):
    # Stable nakli data, frontend development ke liye
    mock_payload = {
        "mandate": {"item": "desk lamp", "max_total": 60, "currency": "USD",
                    "min_rating": 4.0, "max_delivery_days": 7,
                    "blocked_merchants": [], "auto_approve_under": 25},
        "candidates": [
            {"product": {"id": "1", "title": "Basic LED Lamp", "price": 20,
                         "currency": "USD", "rating": 4.5, "merchant": "ShopA",
                         "delivery_days": 3, "url": "https://example.com/1"},
             "decision": {"action": "auto_pay", "reasons": ["within auto-approve limit 25"]}},
            {"product": {"id": "2", "title": "Premium Desk Lamp", "price": 75,
                         "currency": "USD", "rating": 4.8, "merchant": "ShopB",
                         "delivery_days": 2, "url": "https://example.com/2"},
             "decision": {"action": "reject", "reasons": ["price 75 exceeds budget 60"]}},
        ],
        "chosen_id": "1",
        "order": {"id": "MOCK_ORDER_ID", "approve_url": "https://example.com/approve", "product_id": "1"},
        "audit": [
            {"step": "parsed_mandate", "detail": {"item": "desk lamp", "max_total": 60}},
            {"step": "products_found", "detail": {"count": 2}},
            {"step": "rule_check", "detail": {"product_id": "1", "action": "auto_pay", "reasons": ["within auto-approve limit 25"]}},
            {"step": "rule_check", "detail": {"product_id": "2", "action": "reject", "reasons": ["price 75 exceeds budget 60"]}},
            {"step": "ranker_choice", "detail": {"chosen_id": "1", "reason": "Best value", "notes": {"1": "Best value"}}},
            {"step": "order_created", "detail": {"order_id": "MOCK_ORDER_ID"}},
        ],
        "explanation": {
            "summary": "Basic LED Lamp chosen for best value within budget",
            "notes": {"1": "Best value"},
        },
        "monthly_cap": 500,
        "month_spent": 0,
    }
    
    # Store mock run in DB so select endpoint can find it
    run_id = "mock_run_id"
    insert_run(run_id, req.user_email, mock_payload)
    
    return {
        "run_id": run_id,
        **mock_payload,
    }

@app.post("/api/orders/{order_id}/capture")
async def capture(order_id: str):
    order_info = get_order(order_id)
    if not order_info:
        order_info = ORDERS.get(order_id)
        if not order_info:
            raise HTTPException(status_code=404, detail="Order not found")

    if order_info.get("action") == "reject":
        raise HTTPException(status_code=409, detail="Order was rejected, cannot capture")
    if order_info.get("status") == "captured":
        raise HTTPException(status_code=409, detail="Order already captured")

    try:
        result = await capture_order(order_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=e.response.text)

    capture_id = None
    amount = None
    currency = None
    payer_email = None

    try:
        captures = (
            result.get("purchase_units", [{}])[0]
            .get("payments", {})
            .get("captures", [])
        )
        if captures:
            first = captures[0]
            capture_id = first.get("id")
            amt = first.get("amount", {})
            amount = amt.get("value")
            currency = amt.get("currency_code")
    except Exception:
        pass

    try:
        payer_email = result.get("payer", {}).get("email_address")
    except Exception:
        pass

    if capture_id and amount is not None and currency:
        capture_order_db(order_id, capture_id, amount, currency, payer_email)

    if order_id in ORDERS:
        ORDERS[order_id]["captured"] = True

    return {
        "status": result.get("status"),
        "capture_id": capture_id,
        "amount": amount,
        "currency": currency,
        "payer_email": payer_email,
        "title": order_info.get("title"),
        "merchant": order_info.get("merchant"),
    }

@app.post("/api/runs/{run_id}/select")
async def select_product(run_id: str, req: SelectRequest):
    # 1. Fetch run
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    payload = run["payload"]
    user_email = run["user_email"]

    # 2. Check user_email matches
    if req.user_email != user_email:
        raise HTTPException(status_code=403, detail="User mismatch")

    # 3. Find product in candidates
    candidates = payload.get("candidates", [])
    product_map = {c["product"]["id"]: c for c in candidates}
    if req.product_id not in product_map:
        raise HTTPException(status_code=404, detail="Product not found in run")

    candidate = product_map[req.product_id]
    action = candidate["decision"]["action"]

    # 4. Reject if decision is "reject"
    if action == "reject":
        raise HTTPException(status_code=409, detail="Product was rejected")

    # 5. Check monthly cap with current captured spend
    product = candidate["product"]
    price = product["price"]
    currency = product["currency"]
    month_spent = get_monthly_spent(user_email)
    if month_spent + price > MONTHLY_CAP:
        raise HTTPException(
            status_code=409,
            detail=f"Would exceed monthly cap (spent {month_spent:.2f} of {MONTHLY_CAP:.2f})"
        )

    # 6. Check if order already exists for this run_id + product_id
    existing_order = payload.get("order")
    if existing_order and existing_order.get("product_id") == req.product_id:
        # Return existing order
        return {
            "order": existing_order,
            "product": product,
            "decision": candidate["decision"],
        }

    # 7. Create PayPal order using stored product data (ignore client price)
    try:
        o = await create_order(price, currency, product["title"])
        approve_url = next(
            (l["href"] for l in o["links"] if l["rel"] in ("payer-action", "approve")),
            None,
        )
        order = {"id": o["id"], "approve_url": approve_url, "product_id": req.product_id}
    except Exception as e:
        logging.exception("PayPal order creation failed in select")
        raise HTTPException(status_code=502, detail="Could not create payment order")

    # 8. Insert order with status "created" and link to run
    insert_order(
        order_id=o["id"],
        user_email=user_email,
        title=product["title"],
        merchant=product["merchant"],
        amount=price,
        currency=currency,
        action=action,
        demo=1 if user_email == "demo@mandate.app" else 0,
    )

    # 9. Return response
    return {
        "order": order,
        "product": product,
        "decision": candidate["decision"],
    }

@app.get("/paypal/return")
def paypal_return(token: str):
    return RedirectResponse(f"{FRONTEND_URL}/?order={token}")

@app.get("/paypal/cancel")
def paypal_cancel():
    return RedirectResponse(f"{FRONTEND_URL}/?cancelled=1")

@app.get("/api/spending")
async def spending(user: str = Query(default="demo@mandate.app")):
    return get_spending_data(user)
