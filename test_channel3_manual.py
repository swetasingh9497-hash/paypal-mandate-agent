import os, json, httpx
from dotenv import load_dotenv
load_dotenv()

r = httpx.post(
    "https://api.trychannel3.com/v1/search",
    headers={"x-api-key": os.environ["CHANNEL3_API_KEY"],
             "Content-Type": "application/json"},
    json={"query": "desk lamp", "limit": 3},
    timeout=20,
)
print(r.status_code)
print(json.dumps(r.json(), indent=2)[:6000])