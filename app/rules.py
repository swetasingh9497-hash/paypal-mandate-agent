from .schemas import Mandate, Product, Decision

def evaluate(m: Mandate, p: Product) -> Decision:
    violations = []   # rule toota
    unverified = []   # rule check hi nahi ho paya

    if p.currency != m.currency:
        violations.append(f"currency mismatch ({p.currency} vs {m.currency})")
    if p.price > m.max_total:
        violations.append(f"price {p.price} exceeds budget {m.max_total}")
    if p.merchant.lower() in {b.lower() for b in m.blocked_merchants}:
        violations.append(f"merchant {p.merchant} is blocked")

    if m.min_rating is not None:
        if p.rating is None:
            unverified.append(f"rating not available, cannot verify >= {m.min_rating}")
        elif p.rating < m.min_rating:
            violations.append(f"rating {p.rating} below required {m.min_rating}")

    if m.max_delivery_days is not None:
        if p.delivery_days is None:
            unverified.append(f"delivery time not available, cannot verify <= {m.max_delivery_days}d")
        elif p.delivery_days > m.max_delivery_days:
            violations.append(f"delivery {p.delivery_days}d exceeds {m.max_delivery_days}d")

    if violations:
        return Decision(action="reject", reasons=violations)

    if unverified:
        return Decision(action="needs_approval", reasons=unverified)

    if p.price <= m.auto_approve_under:
        return Decision(action="auto_pay",
                        reasons=[f"within auto-approve limit {m.auto_approve_under:g}"])

    return Decision(action="needs_approval",
                    reasons=["passes all rules but above auto-approve limit"])