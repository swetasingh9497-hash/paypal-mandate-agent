import os, httpx

BASE = "https://api-m.sandbox.paypal.com"

async def _token(client: httpx.AsyncClient) -> str:
    r = await client.post(
        f"{BASE}/v1/oauth2/token",
        auth=(os.environ["PAYPAL_CLIENT_ID"], os.environ["PAYPAL_SECRET"]),
        data={"grant_type": "client_credentials"},
    )
    r.raise_for_status()
    return r.json()["access_token"]

async def create_order(amount: float, currency: str, description: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as c:
        token = await _token(c)
        r = await c.post(
            f"{BASE}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "description": description[:127],
                    "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
                }],
                "payment_source": {
                    "paypal": {
                        "experience_context": {
                            "return_url": "http://localhost:8000/paypal/return",
                            "cancel_url": "http://localhost:8000/paypal/cancel",
                            "user_action": "PAY_NOW",
                            "shipping_preference": "NO_SHIPPING",
                        }
                    }
                },
            },
        )
        r.raise_for_status()
        return r.json()   # links mein approval URL hota hai

async def capture_order(order_id: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as c:
        token = await _token(c)
        r = await c.post(
            f"{BASE}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        r.raise_for_status()
        return r.json()