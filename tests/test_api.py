from fastapi.testclient import TestClient
import app.main as m

client = TestClient(m.app)

async def fake_pipeline(text):
    return {"ok": True}

def test_rate_limit(monkeypatch):
    monkeypatch.setattr(m, "run_pipeline", fake_pipeline)
    m._hits.clear()
    codes = [client.post("/api/run", json={"text": "desk lamp under $60"}).status_code
             for _ in range(6)]
    assert codes[:5] == [200] * 5
    assert codes[5] == 429

def test_text_too_long():
    m._hits.clear()
    r = client.post("/api/run", json={"text": "x" * 501})
    assert r.status_code == 422

def test_service_error_returns_503(monkeypatch):
    async def boom(text):
        raise RuntimeError("busy")
    monkeypatch.setattr(m, "run_pipeline", boom)
    m._hits.clear()
    r = client.post("/api/run", json={"text": "desk lamp under $60"})
    assert r.status_code == 503