import os, json
from anthropic import Anthropic
from .schemas import Mandate

client = Anthropic()
MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")

SYSTEM = """Convert the user's shopping request into JSON matching this schema:
{"item": str, "max_total": number, "currency": str, "min_rating": number|null,
 "max_delivery_days": int|null, "blocked_merchants": [str], "auto_approve_under": number}
Rules: output ONLY JSON, no prose, no markdown fences.
If the budget is missing, set max_total to 0 (it will be rejected).
Never invent limits the user did not state. auto_approve_under defaults to 0."""

def parse_mandate(text: str) -> Mandate:
    resp = client.messages.create(
        model=MODEL, max_tokens=500, system=SYSTEM,
        messages=[{"role": "user", "content": text}],
    )
    raw = resp.content[0].text.strip()
    return Mandate.model_validate(json.loads(raw))  # invalid ho toh yahin error