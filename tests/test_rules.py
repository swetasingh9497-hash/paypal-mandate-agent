from app.schemas import Mandate, Product
from app.rules import evaluate

M = Mandate(item="desk lamp", max_total=60, min_rating=4.0,
            max_delivery_days=7, auto_approve_under=25)

def P(**kw):
    base = dict(id="1", title="Lamp", price=20, currency="USD",
                rating=4.5, merchant="Shop", delivery_days=3, url="x")
    return Product(**{**base, **kw})

def test_auto_pay():       assert evaluate(M, P(), 0, 500).action == "auto_pay"
def test_needs_approval():assert evaluate(M, P(price=45), 0, 500).action == "needs_approval"
def test_over_budget():   assert evaluate(M, P(price=80), 0, 500).action == "reject"
def test_low_rating():    assert evaluate(M, P(rating=3.2), 0, 500).action == "reject"
def test_missing_rating():assert evaluate(M, P(rating=None), 0, 500).action == "needs_approval"
def test_boundary_price_eq_max(): assert evaluate(M, P(price=60), 0, 500).action == "needs_approval"
def test_boundary_price_under_max(): assert evaluate(M, P(price=59.99), 0, 500).action == "needs_approval"
def test_missing_delivery(): assert evaluate(M, P(delivery_days=None), 0, 500).action == "needs_approval"

# Monthly cap tests
def test_cap_boundary_passes():
    """spend + price == cap should pass"""
    assert evaluate(M, P(price=50), 450, 500).action == "needs_approval"

def test_cap_exceeded_rejects():
    """spend + price > cap should reject"""
    assert evaluate(M, P(price=51), 450, 500).action == "reject"

def test_cap_exceeded_reason():
    result = evaluate(M, P(price=51), 450, 500)
    assert result.action == "reject"
    assert any("monthly cap" in r.lower() for r in result.reasons)