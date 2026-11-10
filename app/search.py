import os
import logging
import httpx
from .schemas import Mandate, Product

logger = logging.getLogger(__name__)

MOCK_PRODUCTS = [
    Product(id="1", title="Basic LED Desk Lamp", price=20, currency="USD",
            rating=4.5, merchant="ShopA", delivery_days=3, url="https://example.com/1"),
    Product(id="2", title="Premium Adjustable Desk Lamp", price=45, currency="USD",
            rating=4.8, merchant="ShopB", delivery_days=2, url="https://example.com/2"),
    Product(id="3", title="Designer Lamp", price=120, currency="USD",
            rating=4.9, merchant="ShopC", delivery_days=4, url="https://example.com/3"),
    Product(id="4", title="Cheap Lamp", price=9, currency="USD",
            rating=3.1, merchant="ShopD", delivery_days=5, url="https://example.com/4"),
    Product(id="5", title="Slow Lamp", price=30, currency="USD",
            rating=4.6, merchant="ShopE", delivery_days=14, url="https://example.com/5"),
]

async def search_products(mandate: Mandate) -> list[Product]:
    api_key = os.getenv("CHANNEL3_API_KEY")
    if not api_key:
        logger.warning("CHANNEL3_API_KEY not set, using mock data")
        return MOCK_PRODUCTS

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.trychannel3.com/v1/search",
                headers={"x-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "query": mandate.item,
                    "limit": 10,
                    "filters": {"price": {"max_price": mandate.max_total}}
                }
            )
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        logger.warning(f"Channel3 API call failed: {type(e).__name__}: {e}, using mock data")
        return MOCK_PRODUCTS

    products = []
    for item in data.get("products", []):
        # Find the cheapest in-stock offer
        in_stock_offers = [
            offer for offer in item.get("offers", [])
            if offer.get("availability") == "InStock"
        ]
        if not in_stock_offers:
            continue

        best_offer = min(in_stock_offers, key=lambda o: o.get("price", {}).get("price", float("inf")))
        offer_price = best_offer.get("price", {})
        price = offer_price.get("price")
        currency = offer_price.get("currency", "USD")
        merchant = best_offer.get("domain", "Unknown")
        url = best_offer.get("url", "")

        # Rating from product ratings rollup (may be None)
        rating = None
        if item.get("ratings") and item["ratings"].get("value") is not None:
            rating = float(item["ratings"]["value"])

        # Delivery days - not provided by Channel3 API, use None
        delivery_days = None

        products.append(Product(
            id=str(item.get("id", "")),
            title=str(item.get("title", "Unknown Product")),
            price=float(price) if price is not None else 0.0,
            currency=str(currency),
            rating=rating,
            merchant=str(merchant),
            delivery_days=delivery_days,
            url=str(url),
        ))

    return products if products else MOCK_PRODUCTS