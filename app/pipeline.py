from .parser import parse_mandate
from .search import search_products
from .rules import evaluate
from .paypal import create_order
from .ranker import rank_products
from .db import insert_order, get_monthly_spent, MONTHLY_CAP, insert_run
import uuid
import logging

# In-memory order store: order_id -> {product_id, title, merchant, amount, currency, action, captured: false}
# Kept for backward compatibility with capture endpoint
ORDERS = {}

def pick_best_candidate(passing: list[dict]) -> dict | None:
    """
    Choose best non-reject candidate:
    - prefer auto_pay over needs_approval
    - then rating desc (None last)
    - then price asc
    """
    if not passing:
        return None
    def sort_key(c):
        action_prio = 0 if c["decision"].action == "auto_pay" else 1
        rating = c["product"].rating if c["product"].rating is not None else -1
        price = c["product"].price
        return (action_prio, -rating, price)
    passing_sorted = sorted(passing, key=sort_key)
    return passing_sorted[0]

async def run_pipeline(text: str, user_email: str = "demo@mandate.app") -> dict:
    mandate = parse_mandate(text)
    products = await search_products(mandate)

    # Compute monthly spent for cap check
    month_spent = get_monthly_spent(user_email)
    monthly_cap = MONTHLY_CAP

    candidates = [{"product": p, "decision": evaluate(mandate, p, month_spent, monthly_cap)} for p in products]

    # Collect rule results for audit
    rule_results = [
        {"product_id": c["product"].id, "action": c["decision"].action, "reasons": c["decision"].reasons}
        for c in candidates
    ]

    # Filter non-rejected for ranking
    passing = [c for c in candidates if c["decision"].action != "reject"]

    # Rank products (LLM or fallback)
    ranker_result = await rank_products(passing, mandate)
    chosen_id = ranker_result.get("chosen_id") if ranker_result else None
    ranker_summary = ranker_result.get("summary") if ranker_result else None
    ranker_notes = ranker_result.get("notes") if ranker_result else {}
    ranker_choice_reason = f"LLM chose {chosen_id}: {ranker_summary}" if chosen_id else "No passing products"

    chosen = None
    if chosen_id:
        chosen = next((c for c in passing if c["product"].id == chosen_id), None)

    # Fallback to deterministic pick if no LLM choice
    if not chosen:
        chosen = pick_best_candidate(passing)
        if chosen:
            ranker_summary = "Best match by rules"
            ranker_notes = {}
            chosen_id = chosen["product"].id

    order = None
    order_error = None
    if chosen:
        p = chosen["product"]
        try:
            o = await create_order(p.price, p.currency, p.title)
            approve_url = next(
                (l["href"] for l in o["links"] if l["rel"] in ("payer-action", "approve")),
                None,
            )
            order = {"id": o["id"], "approve_url": approve_url}
            # Store in DB for capture lock and spending history
            insert_order(
                order_id=o["id"],
                user_email=user_email,
                title=p.title,
                merchant=p.merchant,
                amount=p.price,
                currency=p.currency,
                action=chosen["decision"].action,
                demo=1 if user_email == "demo@mandate.app" else 0,
            )
            # Also keep in ORDERS for backward compatibility
            ORDERS[o["id"]] = {
                "product_id": p.id,
                "title": p.title,
                "merchant": p.merchant,
                "amount": p.price,
                "currency": p.currency,
                "action": chosen["decision"].action,
                "captured": False,
            }
        except Exception as e:
            logging.exception("PayPal order creation failed")
            order = None
            order_error = "Could not create payment order. Please try again."

    # Build audit
    audit = [
        {"step": "parsed_mandate", "detail": mandate.model_dump()},
        {"step": "products_found", "detail": {"count": len(products)}},
    ]
    audit.extend({"step": "rule_check", "detail": rr} for rr in rule_results)
    if ranker_summary:
        audit.append({"step": "ranker_choice", "detail": {"chosen_id": chosen_id, "reason": ranker_summary, "notes": ranker_notes}})
    if order:
        audit.append({"step": "order_created", "detail": {"order_id": order["id"]}})

    # Prepare response payload for run store
    run_id = uuid.uuid4().hex
    run_payload = {
        "mandate": mandate.model_dump(),
        "candidates": [
            {"product": c["product"].model_dump(), "decision": c["decision"].model_dump()}
            for c in candidates
        ],
        "chosen_id": chosen_id,
        "order": order,
        "audit": audit,
        "explanation": {
            "summary": ranker_summary or "No suitable product found",
            "notes": ranker_notes,
        },
        "monthly_cap": monthly_cap,
        "month_spent": round(month_spent, 2),
    }

    # Store run
    insert_run(run_id, user_email, run_payload)

    response = {
        "run_id": run_id,
        **run_payload,
    }
    if order_error:
        response["order_error"] = order_error

    return response
