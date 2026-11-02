from .parser import parse_mandate
from .search import search_products
from .rules import evaluate
from .paypal import create_order

async def run_pipeline(text: str) -> dict:
    mandate = parse_mandate(text)
    products = await search_products(mandate)

    candidates = [{"product": p, "decision": evaluate(mandate, p)} for p in products]

    # Jo reject nahi hue unme se best: rating zyada, phir price kam.
    # Baad mein yahan LLM ranking aayegi.
    passing = [c for c in candidates if c["decision"].action != "reject"]
    ACTION_PRIORITY = {"auto_pay": 0, "needs_approval": 1}
    passing.sort(key=lambda c: (
    ACTION_PRIORITY[c["decision"].action],
    -(c["product"].rating or 0),
    c["product"].price,
))
    chosen = passing[0] if passing else None

    order = None
    if chosen:
        p = chosen["product"]
        o = await create_order(p.price, p.currency, p.title)
        approve_url = next(
            (l["href"] for l in o["links"] if l["rel"] in ("payer-action", "approve")),
            None,
        )
        order = {"id": o["id"], "approve_url": approve_url}

    return {
        "mandate": mandate.model_dump(),
        "candidates": [
            {"product": c["product"].model_dump(), "decision": c["decision"].model_dump()}
            for c in candidates
        ],
        "chosen_id": chosen["product"].id if chosen else None,
        "order": order,
    }