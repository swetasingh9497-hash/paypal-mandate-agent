from .schemas import Mandate, Product, Decision

def evaluate(m: Mandate, p: Product) -> Decision:
    violations = []

    if p.currency != m.currency:
        violations.append(f"currency mismatch ({p.currency} vs {m.currency})")
    if p.price > m.max_total:
        violations.append(f"price {p.price} exceeds budget {m.max_total}")
    if m.min_rating is not None and (p.rating is None or p.rating < m.min_rating):
        violations.append(f"rating {p.rating} below required {m.min_rating}")
    if m.max_delivery_days is not None and (
        p.delivery_days is None or p.delivery_days > m.max_delivery_days
    ):
        violations.append(f"delivery {p.delivery_days}d exceeds {m.max_delivery_days}d")
    if p.merchant.lower() in {b.lower() for b in m.blocked_merchants}:
        violations.append(f"merchant {p.merchant} is blocked")

    if violations:
        return Decision(action="reject", reasons=violations)

    if p.price <= m.auto_approve_under:
        return Decision(action="auto_pay",
                        reasons=[f"within auto-approve limit {m.auto_approve_under}"])

    return Decision(action="needs_approval",
                    reasons=["passes all rules but above auto-approve limit"])