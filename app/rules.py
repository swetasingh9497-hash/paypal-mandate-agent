from .schemas import Mandate, Product, Decision

def evaluate(m: Mandate, p: Product, month_spent: float = 0, monthly_cap: float = 500) -> Decision:
    violations = []
    needs_approval_reasons = []

    if p.currency != m.currency:
        violations.append(f"currency mismatch ({p.currency} vs {m.currency})")
    if p.price > m.max_total:
        violations.append(f"price {p.price} exceeds budget {m.max_total}")
    if m.min_rating is not None:
        if p.rating is None:
            needs_approval_reasons.append("rating not available, please confirm")
        elif p.rating < m.min_rating:
            violations.append(f"rating {p.rating} below required {m.min_rating}")
    if m.max_delivery_days is not None:
        if p.delivery_days is None:
            needs_approval_reasons.append("delivery time not available, please confirm")
        elif p.delivery_days > m.max_delivery_days:
            violations.append(f"delivery {p.delivery_days}d exceeds {m.max_delivery_days}d")
    if p.merchant.lower() in {b.lower() for b in m.blocked_merchants}:
        violations.append(f"merchant {p.merchant} is blocked")

    # Monthly cap check
    if month_spent + p.price > monthly_cap:
        violations.append(f"would exceed monthly cap (spent {month_spent:.2f} of {monthly_cap:.2f})")

    if violations:
        return Decision(action="reject", reasons=violations)

    if needs_approval_reasons:
        return Decision(action="needs_approval", reasons=needs_approval_reasons)

    if p.price <= m.auto_approve_under:
        return Decision(action="auto_pay",
                        reasons=[f"within auto-approve limit {m.auto_approve_under}"])

    return Decision(action="needs_approval",
                    reasons=["passes all rules but above auto-approve limit"])