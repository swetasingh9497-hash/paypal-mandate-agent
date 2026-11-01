from .schemas import Mandate, Product

async def search_products(mandate: Mandate) -> list[Product]:
    # TEMP: nakli data. Channel3 aane par sirf is function ki body badlegi.
    return [
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