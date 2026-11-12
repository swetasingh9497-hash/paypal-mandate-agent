
from .parser import parse_mandate
from .search import search_products
from .rules import evaluate
from .ranker import rank_products, bayesian_rating
from .db import (
    get_monthly_spent,
    MONTHLY_CAP,
    insert_run,
    DEMO_EMAIL,
)

import uuid
import logging
import re


ORDERS = {}


_STOP = {
    "under", "below", "over", "above", "rating",
    "with", "for", "and", "the", "buy",
    "autopay", "auto", "approve", "pay",
    "less", "than", "max", "min",
}


def _query_tokens(text: str) -> set[str]:
    return {
        t
        for t in re.findall(r"[a-z]+", text.lower())
        if len(t) > 2 and t not in _STOP
    }


def pick_best_candidate(
    passing: list[dict],
    text: str = "",
) -> dict | None:
    """
    Deterministic fallback ranking.

    Priority:
    1. User keyword relevance.
    2. Auto-pay eligibility.
    3. Bayesian rating (rating + review volume).
    4. Raw rating as tie-breaker.
    5. Price.
    """

    if not passing:
        return None

    tokens = _query_tokens(text)

    def sort_key(c):
        p = c["product"]

        title = (p.title or "").lower()

        relevance = sum(
            t in title
            for t in tokens
        )

        confidence_rating = bayesian_rating(
            p.rating,
            p.review_count,
        )

        action_priority = (
            0
            if c["decision"].action == "auto_pay"
            else 1
        )

        return (
            -relevance,
            action_priority,
            -confidence_rating,
            -(p.rating if p.rating is not None else 0),
            p.price,
        )

    return sorted(
        passing,
        key=sort_key,
    )[0]


async def run_pipeline(
    text: str,
    user_email: str = DEMO_EMAIL,
) -> dict:

    mandate = parse_mandate(text)

    products = await search_products(mandate)

    month_spent = get_monthly_spent(user_email)

    monthly_cap = MONTHLY_CAP

    candidates = [
        {
            "product": p,
            "decision": evaluate(
                mandate,
                p,
                month_spent,
                monthly_cap,
            ),
        }
        for p in products
    ]

    rule_results = [
        {
            "product_id": c["product"].id,
            "action": c["decision"].action,
            "reasons": c["decision"].reasons,
        }
        for c in candidates
    ]

    passing = [
        c
        for c in candidates
        if c["decision"].action != "reject"
    ]

    ranker_result = await rank_products(
        passing,
        mandate,
        user_query=text,
    )

    chosen_id = (
        ranker_result.get("chosen_id")
        if ranker_result
        else None
    )

    ranker_summary = (
        ranker_result.get("summary")
        if ranker_result
        else None
    )

    ranker_notes = (
        ranker_result.get("notes")
        if ranker_result
        else {}
    )

    chosen = None

    if chosen_id:
        chosen = next(
            (
                c
                for c in passing
                if c["product"].id == chosen_id
            ),
            None,
        )

    if not chosen:
        chosen = pick_best_candidate(
            passing,
            text,
        )

        if chosen:
            ranker_summary = (
                "Fallback pick (AI ranker unavailable): "
                "keyword relevance, approval eligibility, "
                "confidence-adjusted rating and price."
            )

            ranker_notes = {}

            chosen_id = chosen["product"].id

    # Order creation is deferred to the selection endpoint
    order = None

    audit = [
        {
            "step": "parsed_mandate",
            "detail": mandate.model_dump(),
        },
        {
            "step": "products_found",
            "detail": {
                "count": len(products)
            },
        },
    ]

    audit.extend(
        {
            "step": "rule_check",
            "detail": result,
        }
        for result in rule_results
    )

    if ranker_summary:
        audit.append(
            {
                "step": "ranker_choice",
                "detail": {
                    "chosen_id": chosen_id,
                    "reason": ranker_summary,
                    "notes": ranker_notes,
                },
            }
        )

    run_id = uuid.uuid4().hex

    run_payload = {
        "mandate": mandate.model_dump(),

        "candidates": [
            {
                "product": c["product"].model_dump(),
                "decision": c["decision"].model_dump(),
            }
            for c in candidates
        ],

        "chosen_id": chosen_id,
        "order": order,
        "audit": audit,

        "explanation": {
            "summary": (
                ranker_summary
                or "No suitable product found"
            ),
            "notes": ranker_notes,
        },

        "monthly_cap": monthly_cap,
        "month_spent": round(month_spent, 2),
    }

    insert_run(
        run_id,
        user_email,
        run_payload,
    )

    response = {
        "run_id": run_id,
        **run_payload,
    }

    return response
