import sys, asyncio
from dotenv import load_dotenv
load_dotenv()
from app.paypal import capture_order

result = asyncio.run(capture_order(sys.argv[1]))
print("status:", result["status"])