
import os
import logging
import httpx

from .schemas import Mandate, Product

logger = logging.getLogger(__name__)


MOCK_PRODUCTS = [
    Product(
        id="1",
        title="Basic LED Desk Lamp",
        price=20,
        currency="USD",
        rating=4.5,
        merchant="ShopA",
        delivery_days=3,
        url="https://example.com/1",
    ),
    Product(
        id="2",
        title="Premium Adjustable Desk Lamp",
        price=45,
        currency="USD",
        rating=4.8,
        merchant="ShopB",
        delivery_days=2,
        url="https://example.com/2",
    ),
    Product(
        id="3",
        title="Designer Lamp",
        price=120,
        currency="USD",
        rating=4.9,
        merchant="ShopC",
        delivery_days=4,
        url="https://example.com/3",
    ),
    Product(
        id="4",
        title="Cheap Lamp",
        price=9,
        currency="USD",
        rating=3.1,
        merchant="ShopD",
        delivery_days=5,
        url="https://example.com/4",
    ),
    Product(
        id="5",
        title="Slow Lamp",
        price=30,
        currency="USD",
        rating=4.6,
        merchant="ShopE",
        delivery_days=14,
        url="https://example.com/5",
    ),
]


def extract_rating_data(item: dict) -> tuple:
    """
    Extract average rating and total review count
    from Channel3 ratings object.

    Channel3 format:
    {
        "value": 4.7,
        "count": 887,
        "source_count": 3
    }
    """

    ratings = item.get("ratings") or {}

    rating = None
    review_count = None

    raw_rating = ratings.get("value")
    raw_count = ratings.get("count")

    try:
        if raw_rating is not None:
            rating = float(raw_rating)

            if not 0 <= rating <= 5:
                rating = None

    except (ValueError, TypeError):
        rating = None

    try:
        if raw_count is not None:
            review_count = int(raw_count)

            if review_count < 0:
                review_count = None

    except (ValueError, TypeError):
        review_count = None

    return rating, review_count


async def search_products(mandate: Mandate) -> list[Product]:

    api_key = os.getenv("CHANNEL3_API_KEY")

    if not api_key:
        logger.warning(
            "CHANNEL3_API_KEY not set, using mock data"
        )
        return MOCK_PRODUCTS

    try:

        async with httpx.AsyncClient(timeout=15.0) as client:

            response = await client.post(
                "https://api.trychannel3.com/v1/search",

                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json",
                },

                json={
                    "query": mandate.item,
                    "limit": 10,
                    "filters": {
                        "price": {
                            "max_price": mandate.max_total
                        }
                    },
                },
            )

            response.raise_for_status()
            data = response.json()

    except Exception as e:

        logger.warning(
            "Channel3 API call failed: %s: %s",
            type(e).__name__,
            e,
        )

        return MOCK_PRODUCTS


    products = []

    for item in data.get("products", []):

        # Find cheapest in-stock offer
        in_stock_offers = [
            offer
            for offer in item.get("offers", [])
            if offer.get("availability") == "InStock"
        ]

        if not in_stock_offers:
            continue

        best_offer = min(
            in_stock_offers,
            key=lambda o: o.get(
                "price", {}
            ).get(
                "price", float("inf")
            ),
        )

        offer_price = best_offer.get("price", {})

        price = offer_price.get("price")
        currency = offer_price.get("currency", "USD")

        merchant = best_offer.get("domain", "Unknown")
        url = best_offer.get("url", "")

        # Extract rating and review count
        rating, review_count = extract_rating_data(item)

        # Channel3 does not provide delivery days
        delivery_days = None

        try:

            if price is None:
                continue

            products.append(
                Product(
                    id=str(item.get("id", "")),
                    title=str(
                        item.get("title", "Unknown Product")
                    ),
                    price=float(price),
                    currency=str(currency),
                    rating=rating,
                    review_count=review_count,
                    merchant=str(merchant),
                    delivery_days=delivery_days,
                    url=str(url),
                )
            )

        except (ValueError, TypeError) as e:

            logger.warning(
                "Skipping invalid product %s: %s",
                item.get("id"),
                e,
            )

    return products if products else MOCK_PRODUCTS
