from dotenv import load_dotenv
load_dotenv()

import os
import time
import logging
from collections import defaultdict, deque
import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from .paypal import capture_order, create_order
from .pipeline import run_pipeline, ORDERS
from .db import (
    get_order, capture_order_db, supersede_order_db, replace_order_atomic, get_spending_data, get_run, insert_order,
    insert_run, update_run_payload, get_monthly_spent, MONTHLY_CAP, DEMO_EMAIL,
)
from .auth import router as auth_router, resolve_user, require_user

# Environment configuration with safe defaults
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

# Startup logging (no secrets)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting Budgie API")
logger.info("CORS allowed origins: %s", CORS_ORIGINS)
logger.info("Frontend URL: %s", FRONTEND_URL)
logger.info("Backend URL: %s", BACKEND_URL)

# --- simple per-IP rate limit (memory mein, restart par reset hota hai) ---
_hits = defaultdict(deque)

RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "20"))

def rate_limit(request: Request, limit: int = RATE_LIMIT_PER_MIN, window: int = 60):
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

app = FastAPI(title="Budgie")
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunRequest(BaseModel):
    text: str = Field(min_length=3, max_length=500)

class SelectRequest(BaseModel):
    product_id: str
    approved: bool = False  # Must be true for needs_approval products

@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/run")
async def run(req: RunRequest, request: Request):
    rate_limit(request)
    # Strict authentication: require valid Bearer token
    user = require_user(request)
    try:
        return await run_pipeline(req.text, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=503, detail="The AI service is not available right now. Please try again.")
    except httpx.HTTPStatusError as e:
        logger.warning("Upstream HTTP error: %s", e.response.status_code)
        raise HTTPException(status_code=502, detail="Could not create the payment order. Please try again.")
    except Exception:
        logging.exception("Unhandled error in /api/run")
        raise HTTPException(status_code=503, detail="The AI service is not available right now. Please try again.")

@app.post("/api/mock/run")
async def run_mock(req: RunRequest, request: Request):
    # Stable mock data for frontend development
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

    # Strict authentication for mock endpoint too
    user = require_user(request)

    # Store mock run in DB so select endpoint can find it
    run_id = "mock_run_id"
    insert_run(run_id, user, mock_payload)

    return {
        "run_id": run_id,
        **mock_payload,
    }

@app.post("/api/orders/{order_id}/capture")
async def capture(order_id: str, request: Request):
    # Strict authentication
    user = require_user(request)

    # Order must exist in persistent storage
    order_info = get_order(order_id)
    if not order_info:
        raise HTTPException(status_code=404, detail="Order not found")

    # Only the owner of the order may capture it
    owner = order_info.get("user_email")
    if not owner:
        raise HTTPException(status_code=403, detail="Order has no owner")
    if user != str(owner).strip().lower():
        raise HTTPException(status_code=403, detail="This order belongs to another user")

    if order_info.get("action") == "reject":
        raise HTTPException(status_code=409, detail="Order was rejected, cannot capture")

    # Only allow capture for orders with status 'created'
    if order_info.get("status") != "created":
        raise HTTPException(status_code=409, detail=f"Order cannot be captured (status: {order_info.get('status')})")

    try:
        result = await capture_order(order_id)
    except httpx.HTTPStatusError as e:
        logger.warning("PayPal HTTP error: %s", e.response.status_code)
        raise HTTPException(status_code=502, detail="Payment could not be captured. Please try again.")
    except Exception:
        logging.exception("Capture failed")
        raise HTTPException(status_code=502, detail="Payment could not be captured. Please try again.")

    # Verify PayPal order status is COMPLETED
    paypal_status = result.get("status")
    if paypal_status != "COMPLETED":
        raise HTTPException(status_code=409, detail=f"Payment not completed (status: {paypal_status})")

    capture_id = None
    amount = None
    currency = None
    payer_email = None
    capture_status = None

    try:
        captures = (
            result.get("purchase_units", [{}])[0]
            .get("payments", {})
            .get("captures", [])
        )
        if captures:
            first = captures[0]
            capture_id = first.get("id")
            capture_status = first.get("status")
            amt = first.get("amount", {})
            amount = amt.get("value")
            currency = amt.get("currency_code")
    except Exception:
        pass

    try:
        payer_email = result.get("payer", {}).get("email_address")
    except Exception:
        pass

    # Verify capture status is COMPLETED - missing or non-COMPLETED status is rejected
    if capture_status is None or capture_status != "COMPLETED":
        raise HTTPException(status_code=409, detail=f"Capture not completed (status: {capture_status})")

    # Verify required capture fields exist
    if not capture_id or amount is None or not currency:
        raise HTTPException(status_code=409, detail="Invalid capture response: missing capture ID, amount, or currency")

    # Attempt to capture in database with validation
    if not capture_order_db(order_id, capture_id, amount, currency, payer_email):
        raise HTTPException(status_code=409, detail="Capture failed: order already captured, amount/currency mismatch, or invalid state")

    if order_id in ORDERS:
        ORDERS[order_id]["captured"] = True

    return {
        "status": paypal_status,
        "capture_id": capture_id,
        "amount": amount,
        "currency": currency,
        "payer_email": payer_email,
        "title": order_info.get("title"),
        "merchant": order_info.get("merchant"),
    }

@app.post("/api/runs/{run_id}/select")
async def select_product(run_id: str, req: SelectRequest, request: Request):
    rate_limit(request)

    # 1. Fetch run
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    payload = run["payload"]
    user_email = run["user_email"]

    # 2. Only the user who made the run may select from it (strict auth)
    user = require_user(request)
    if user != str(user_email).strip().lower():
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

    # 5. For needs_approval products, require explicit confirmation
    if action == "needs_approval" and not req.approved:
        raise HTTPException(status_code=409, detail="This product requires explicit approval. Set 'approved=true' to confirm.")

    # 6. Check monthly cap with current captured spend
    product = candidate["product"]
    price = product["price"]
    currency = product["currency"]
    month_spent = get_monthly_spent(user_email)
    if month_spent + price > MONTHLY_CAP:
        raise HTTPException(
            status_code=409,
            detail=f"Would exceed monthly cap (spent {month_spent:.2f} of {MONTHLY_CAP:.2f})"
        )

    # 7. Check if order already exists for this run_id + product_id
    existing_order = payload.get("order")
    if existing_order and existing_order.get("product_id") == req.product_id:
        # Same product selected again - return existing valid created order
        # Check DB status if order exists in DB; if not in DB (e.g., mock order), allow it
        db_order = get_order(existing_order["id"])
        if db_order is None or db_order.get("status") == "created":
            # Order not in DB (mock) or still created - return it
            return {
                "order": existing_order,
                "product": product,
                "decision": candidate["decision"],
            }
        # If order exists in DB but is no longer created (superseded/captured), fall through to create new order

    # 8. If switching to a different product, remember the previous order ID
    prev_order_id = None
    if existing_order and existing_order.get("product_id") != req.product_id:
        prev_order_id = existing_order["id"]

    # 9. Create PayPal order using stored product data (ignore client price)
    try:
        o = await create_order(price, currency, product["title"])
        approve_url = next(
            (l["href"] for l in o["links"] if l["rel"] in ("payer-action", "approve")),
            None,
        )
        order = {"id": o["id"], "approve_url": approve_url, "product_id": req.product_id}
    except httpx.HTTPStatusError as e:
        logger.warning("PayPal HTTP error: %s", e.response.status_code)
        raise HTTPException(status_code=502, detail="Could not create the payment order. Please try again.")
    except Exception:
        logging.exception("PayPal order creation failed in select")
        raise HTTPException(status_code=502, detail="Could not create the payment order. Please try again.")

    # 9. Atomically: insert new order, update run payload, supersede previous (if switching)
    new_order_data = {
        "order_id": o["id"],
        "user_email": user_email,
        "title": product["title"],
        "merchant": product["merchant"],
        "amount": price,
        "currency": currency,
        "action": action,
        "demo": 1 if user_email == DEMO_EMAIL else 0,
    }

    new_order_payload = {**payload, "order": order}

    try:
        replace_order_atomic(
            prev_order_id=prev_order_id,
            new_order_id=o["id"],
            user_email=user_email,
            run_id=run_id,
            new_order_payload=new_order_payload,
            new_order_data=new_order_data,
        )
    except RuntimeError as e:
        error_msg = str(e)
        if "belongs to another user" in error_msg:
            raise HTTPException(status_code=403, detail="This order belongs to another user")
        if "not in 'created' status" in error_msg:
            raise HTTPException(status_code=409, detail=f"Order cannot be superseded (status: not created)")
        if "not found" in error_msg:
            raise HTTPException(status_code=409, detail=f"Previous order not found")
        if "Failed to update run payload" in error_msg or "Failed to supersede" in error_msg or "Failed to insert" in error_msg:
            raise HTTPException(status_code=502, detail="Order replacement failed")
        raise HTTPException(status_code=502, detail="Order replacement failed")
    except Exception:
        logging.exception("Order replacement failed")
        raise HTTPException(status_code=502, detail="Order replacement failed")

    # 12. Return response
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
async def spending(request: Request):
    user = require_user(request)
    return get_spending_data(user)