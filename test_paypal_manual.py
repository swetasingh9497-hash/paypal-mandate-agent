import asyncio
from dotenv import load_dotenv
load_dotenv()
from app.paypal import create_order

result = asyncio.run(create_order(10, "USD", "test order"))
print("order id:", result["id"])
print("status:", result["status"])
for link in result["links"]:
    print(link["rel"], link["href"])