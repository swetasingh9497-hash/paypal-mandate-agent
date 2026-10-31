from app.schemas import Mandate, Product
from app.rules import evaluate

M = Mandate(item="desk lamp", max_total=60, min_rating=4.0,
            max_delivery_days=7, auto_approve_under=25)

def P(**kw):
    base = dict(id="1", title="Lamp", price=20, currency="USD",
                rating=4.5, merchant="Shop", delivery_days=3, url="x")
    return Product(**{**base, **kw})

def test_auto_pay():       assert evaluate(M, P()).action == "auto_pay"
def test_needs_approval():assert evaluate(M, P(price=45)).action == "needs_approval"
def test_over_budget():   assert evaluate(M, P(price=80)).action == "reject"
def test_low_rating():    assert evaluate(M, P(rating=3.2)).action == "reject"
def test_missing_rating():assert evaluate(M, P(rating=None)).action == "reject"