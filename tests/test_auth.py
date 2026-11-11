import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.auth as auth


class FakeRequest:
    def __init__(self, token=None):
        self.headers = {"authorization": f"Bearer {token}"} if token else {}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "auth_test.db"))
    api = FastAPI()
    api.include_router(auth.router)
    return TestClient(api)


def _register(client, email="a@x.com", pw="password1"):
    return client.post("/api/auth/register", json={"email": email, "password": pw, "name": "Ann"})


def test_register_login_and_me(client):
    r = _register(client, "A@X.com")
    assert r.status_code == 200 and r.json()["user"]["email"] == "a@x.com"
    assert "password1" not in r.text
    r = client.post("/api/auth/login", json={"email": "a@x.com", "password": "password1"})
    assert r.status_code == 200
    token = r.json()["token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "a@x.com"


def test_duplicate_email_is_409(client):
    assert _register(client).status_code == 200
    assert _register(client).status_code == 409


def test_wrong_password_and_unknown_email_same_message(client):
    _register(client)
    bad_pw = client.post("/api/auth/login", json={"email": "a@x.com", "password": "nope-nope"})
    unknown = client.post("/api/auth/login", json={"email": "z@x.com", "password": "password1"})
    assert bad_pw.status_code == unknown.status_code == 401
    assert bad_pw.json()["detail"] == unknown.json()["detail"] == "Invalid email or password"


def test_short_password_rejected(client):
    assert _register(client, pw="short").status_code == 422


def test_tampered_and_expired_tokens(monkeypatch):
    token = auth.make_token("a@x.com")
    assert auth.read_token(token) == "a@x.com"
    assert auth.read_token(token[:-2] + "xx") is None
    monkeypatch.setattr(auth, "TOKEN_TTL", -10)
    assert auth.read_token(auth.make_token("a@x.com")) is None


def test_resolve_user_token_wins_over_fallback():
    token = auth.make_token("real@x.com")
    assert auth.resolve_user(FakeRequest(token), "spoof@x.com") == "real@x.com"
    assert auth.resolve_user(FakeRequest(), "Other@X.com ") == "other@x.com"


def test_bad_token_gives_401():
    with pytest.raises(HTTPException) as e:
        auth.resolve_user(FakeRequest("garbage.token"), "a@x.com")
    assert e.value.status_code == 401


def test_demo_login_and_switch(client, monkeypatch):
    assert client.post("/api/auth/demo").status_code == 200
    monkeypatch.setenv("ALLOW_DEMO_LOGIN", "0")
    assert client.post("/api/auth/demo").status_code == 403