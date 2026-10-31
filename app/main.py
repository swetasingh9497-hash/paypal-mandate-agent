from dotenv import load_dotenv
load_dotenv()

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from .paypal import capture_order

app = FastAPI(title="Mandate")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunRequest(BaseModel):
    text: str

@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/run")
async def run(req: RunRequest):
    # MOCK: baad mein asli pipeline se replace hoga
    return {
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
        "order": {"id": "MOCK_ORDER_ID", "approve_url": "https://example.com/approve"},
    }

@app.post("/api/orders/{order_id}/capture")
async def capture(order_id: str):
    try:
        result = await capture_order(order_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=e.response.text)
    return {"status": result["status"]}

@app.get("/paypal/return")
def paypal_return(token: str):
    # PayPal approve ke baad yahan bhejta hai; token = order id
    return RedirectResponse(f"http://localhost:5173/?order={token}")

@app.get("/paypal/cancel")
def paypal_cancel():
    return RedirectResponse("http://localhost:5173/?cancelled=1")