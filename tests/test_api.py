from fastapi.testclient import TestClient
import app.main as m

client = TestClient(m.app)

async def fake_pipeline(text, user_email="demo@budgie.app"):
    return {"ok": True, "run_id": "test", "mandate": {}, "candidates": [], "chosen_id": None, "order": None, "audit": [], "explanation": {}, "monthly_cap": 500, "month_spent": 0}

def test_rate_limit(monkeypatch):
    monkeypatch.setattr(m, "run_pipeline", fake_pipeline)
    # Access the internal rate limit state
    import app.main as main_mod
    main_mod._hits.clear()
    # Rate limit is now 20 per minute
    codes = [client.post("/api/run", json={"text": "desk lamp under $60", "user_email": "test@test.com"}).status_code
             for _ in range(21)]
    assert codes[:20] == [200] * 20
    assert codes[20] == 429

def test_text_too_long():
    import app.main as main_mod
    main_mod._hits.clear()
    r = client.post("/api/run", json={"text": "x" * 501, "user_email": "test@test.com"})
    assert r.status_code == 422

def test_service_error_returns_503(monkeypatch):
    async def boom(text, user_email="demo@budgie.app"):
        raise RuntimeError("busy")
    monkeypatch.setattr(m, "run_pipeline", boom)
    import app.main as main_mod
    main_mod._hits.clear()
    r = client.post("/api/run", json={"text": "desk lamp under $60", "user_email": "test@test.com"})
    assert r.status_code == 503
