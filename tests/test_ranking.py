import app.ranking as r
from app.schemas import Product, Decision

def C(i, price):
    return {
        "product": Product(id=i, title="Lamp " + i, price=price, currency="USD",
                           merchant="m", url="x"),
        "decision": Decision(action="needs_approval", reasons=[]),
    }

def test_invented_id_ignored(monkeypatch):
    monkeypatch.setattr(r, "complete_json",
                        lambda s, u: '{"ranked_ids":["HACK","b"],"explanation":"ok"}')
    ordered, _ = r.rank_with_llm("lamp", [C("a", 10), C("b", 20)])
    assert [c["product"].id for c in ordered] == ["b", "a"]

def test_garbage_falls_back(monkeypatch):
    monkeypatch.setattr(r, "complete_json", lambda s, u: "not json")
    ordered, exp = r.rank_with_llm("lamp", [C("a", 10), C("b", 20)])
    assert ordered[0]["product"].id == "a"
    assert exp == r.FALLBACK
