from fastapi.testclient import TestClient
import app.main as m

client = TestClient(m.app)

async def fake_pipeline(text, user_email="demo@mandate.app"):
    return {"ok": True, "run_id": "test", "mandate": {}, "candidates": [], "chosen_id": None, "order": None, "audit": [], "explanation": {}, "monthly_cap": 500, "month_spent": 0}

def test_rate_limit(monkeypatch):
    monkeypatch.setattr(m, "run_pipeline", fake_pipeline)
    # Access the internal rate limit state
    import app.main as main_mod
    main_mod._hits.clear()
    codes = [client.post("/api/run", json={"text": "desk lamp under $60", "user_email": "test@test.com"}).status_code
             for _ in range(6)]
    assert codes[:5] == [200] * 5
    assert codes[5] == 429

def test_text_too_long():
    import app.main as main_mod
    main_mod._hits.clear()
    r = client.post("/api/run", json={"text": "x" * 501, "user_email": "test@test.com"})
    assert r.status_code == 422

def test_service_error_returns_503(monkeypatch):
    async def boom(text, user_email="demo@mandate.app"):
        raise RuntimeError("busy")
    monkeypatch.setattr(m, "run_pipeline", boom)
    import app.main as main_mod
    main_mod._hits.clear()
    r = client.post("/api/run", json={"text": "desk lamp under $60", "user_email": "test@test.com"})
    assert r.status_code == 503
