import pytest
from app.schemas import Mandate
from app.parser import check_grounded

def M(**kw):
    return Mandate(**{**dict(item="lamp", max_total=60), **kw})

def test_budget_in_text_ok():
    check_grounded(M(max_total=60), "lamp under $60")

def test_comma_amount_ok():
    check_grounded(M(max_total=1000), "laptop under $1,000")

def test_invented_budget_rejected():
    with pytest.raises(ValueError):
        check_grounded(M(max_total=1), "I want a desk lamp")

def test_invented_auto_approve_rejected():
    with pytest.raises(ValueError):
        check_grounded(M(max_total=60, auto_approve_under=25), "lamp under $60")