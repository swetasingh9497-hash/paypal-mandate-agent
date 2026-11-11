import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .db import DEMO_EMAIL

logger = logging.getLogger("budgie.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])

_SECRET = os.getenv("AUTH_SECRET") or secrets.token_urlsafe(48)
if not os.getenv("AUTH_SECRET"):
    logger.warning("AUTH_SECRET is not set: logins reset on every restart")

TOKEN_TTL = 7 * 24 * 3600
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
BAD_LOGIN = "Invalid email or password"


def _norm(email) -> str:
    return (email or "").strip().lower()


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(os.getenv("DB_PATH", "./orders.db"))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "email TEXT PRIMARY KEY, name TEXT, password_hash TEXT, "
        "salt TEXT, created_at REAL)"
    )
    return conn


def _hash(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 200_000
    ).hex()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str) -> str:
    return _b64(hmac.new(_SECRET.encode(), payload.encode(), hashlib.sha256).digest())


def make_token(email: str) -> str:
    body = {"email": _norm(email), "exp": int(time.time()) + TOKEN_TTL}
    payload = _b64(json.dumps(body).encode())
    return f"{payload}.{_sign(payload)}"


def read_token(token: str):
    try:
        payload, sig = token.split(".", 1)
        if not hmac.compare_digest(sig, _sign(payload)):
            return None
        data = json.loads(_unb64(payload))
        if data.get("exp", 0) < time.time():
            return None
        return data.get("email") or None
    except Exception:
        return None


def resolve_user(request: Request, fallback=None) -> str:
    """Token user if a Bearer token is sent, otherwise the fallback email."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        email = read_token(auth[7:].strip())
        if not email:
            raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
        return email
    return _norm(fallback) or _norm(DEMO_EMAIL)


class RegisterBody(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(min_length=8, max_length=200)
    name: str | None = Field(default=None, max_length=80)


class LoginBody(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(max_length=200)


def _session(email: str, name: str) -> dict:
    return {"token": make_token(email), "user": {"email": email, "name": name}}


@router.post("/register")
def register(body: RegisterBody):
    email = _norm(body.email)
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    name = (body.name or "").strip() or email.split("@")[0]
    salt = secrets.token_hex(16)
    conn = _db()
    try:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        conn.execute(
            "INSERT INTO users (email, name, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?)",
            (email, name, _hash(body.password, salt), salt, time.time()),
        )
        conn.commit()
    finally:
        conn.close()
    return _session(email, name)


@router.post("/login")
def login(body: LoginBody):
    email = _norm(body.email)
    conn = _db()
    try:
        row = conn.execute(
            "SELECT name, password_hash, salt FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        _hash(body.password, "00" * 16)  # same work for unknown emails
        raise HTTPException(status_code=401, detail=BAD_LOGIN)
    name, stored, salt = row
    if not hmac.compare_digest(stored, _hash(body.password, salt)):
        raise HTTPException(status_code=401, detail=BAD_LOGIN)
    return _session(email, name or email.split("@")[0])


@router.post("/demo")
def demo():
    if os.getenv("ALLOW_DEMO_LOGIN", "1") == "0":
        raise HTTPException(status_code=403, detail="Demo login is disabled")
    return _session(_norm(DEMO_EMAIL), "Demo Buyer")


@router.get("/me")
def me(request: Request):
    auth = request.headers.get("authorization", "")
    email = read_token(auth[7:].strip()) if auth.lower().startswith("bearer ") else None
    if not email:
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
    conn = _db()
    try:
        row = conn.execute("SELECT name FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        conn.close()
    default = "Demo Buyer" if email == _norm(DEMO_EMAIL) else email.split("@")[0]
    return {"email": email, "name": (row[0] if row else None) or default}