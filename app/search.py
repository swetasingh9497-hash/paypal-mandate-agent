import os
import httpx
from .schemas import Mandate, Product

API = "https://api.trychannel3.com/v1/search"

def _best_offer(offers, currency):
    ok = []
    for o in offers or []:
        price = (o.get("price") or {})
        if (o.get("availability") == "InStock"
                and o.get("condition", "new") == "new"
                and price.get("currency") == currency
                and price.get("price") is not None):
            ok.append(o)
    return min(ok, key=lambda o: o["price"]["price"]) if ok else None

async def search_products(mandate: Mandate, limit: int = 10) -> list[Product]:
    query = f"{mandate.item} under ${mandate.max_total:g}"
    async with httpx.AsyncClient(timeout=20) as c:
        try:
            r = await c.post(
                API,
                headers={"x-api-key": os.environ["CHANNEL3_API_KEY"],
                         "Content-Type": "application/json"},
                json={"query": query, "limit": limit},
            )
            r.raise_for_status()
        except httpx.HTTPError:
            raise RuntimeError("Product search is unavailable right now. Please try again.")

    products = []
    for p in r.json().get("products", []):
        offer = _best_offer(p.get("offers"), mandate.currency)
        if offer is None:
            continue
        products.append(Product(
            id=p["id"],
            title=p["title"],
            price=offer["price"]["price"],
            currency=offer["price"]["currency"],
            rating=None,          # Channel3 se abhi nahi mil raha
            merchant=offer.get("domain") or "unknown",
            delivery_days=None,   # Channel3 deta hi nahi
            url=offer["url"],
        ))
    return products