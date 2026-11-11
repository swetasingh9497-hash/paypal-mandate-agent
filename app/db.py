import os
import sqlite3
import atexit
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import uuid

DB_PATH = os.getenv("DB_PATH", "./orders.db")
MONTHLY_CAP = float(os.getenv("MONTHLY_CAP", "500"))
SEED_DEMO = os.getenv("SEED_DEMO", "0") == "1"
DEMO_EMAIL = "demo@budgie.app"

# Session storage for local token-based auth (used by main.py for /api/spending)
_session: Optional[Dict[str, Any]] = None

def read_session() -> Optional[Dict[str, Any]]:
    """Read the current session from memory (set by auth flow)."""
    return _session

def set_session(session_data: Optional[Dict[str, Any]]) -> None:
    """Set the current session in memory."""
    global _session
    _session = session_data

_conn: Optional[sqlite3.Connection] = None
_test_conn: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    global _conn, _test_conn
    if _test_conn is not None:
        return _test_conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON")
        init_db(_conn)
        if SEED_DEMO:
            seed_demo(_conn)
    return _conn


def set_test_connection(conn: sqlite3.Connection) -> None:
    global _test_conn
    _test_conn = conn
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)


@contextmanager
def db_cursor():
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def init_db(conn: sqlite3.Connection) -> None:
    # orders table (existing)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            title TEXT NOT NULL,
            merchant TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'created',
            capture_id TEXT,
            created_at TEXT NOT NULL,
            captured_at TEXT,
            demo INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_user_email ON orders(user_email)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)
    """)

    # runs table (new)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_runs_user_email ON runs(user_email)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at)
    """)


def seed_demo_for_user(
    conn: sqlite3.Connection,
    user_email: str,
    now: Optional[datetime] = None,
) -> None:
    """Seed ~14 captured demo orders for a specific user if they have none.
    Guarantees at least 3 orders in the current calendar month (1st of month to now),
    totaling ~240 USD (scaled to stay <= MONTHLY_CAP), with the rest spread over
    the previous 8 weeks and 6 months so both charts have data.
    """
    if now is None:
        now = datetime.utcnow()

    cur = conn.cursor()
    # Check if user already has ANY captured orders (demo or real)
    cur.execute("SELECT COUNT(*) FROM orders WHERE user_email = ? AND status = 'captured'", (user_email,))
    if cur.fetchone()[0] > 0:
        return

    import random
    from datetime import timedelta

    month_start = datetime(now.year, now.month, 1)
    month_elapsed = (now - month_start).total_seconds()
    monthly_cap = MONTHLY_CAP

    # --- Current month orders: at least 3, totaling ~240 USD (capped to MONTHLY_CAP) ---
    # Use fractions of elapsed time so they work even when only hours into the month
    fractions = [0.1, 0.3, 0.5, 0.7, 0.9]
    base_products = [
        ("Basic LED Lamp", "ShopA", 20, "auto_pay"),
        ("Wireless Mouse", "ShopB", 35, "needs_approval"),
        ("USB-C Hub", "ShopD", 45, "auto_pay"),
        ("Desk Lamp", "ShopA", 30, "auto_pay"),
        ("Monitor Stand", "ShopE", 55, "needs_approval"),
        ("Webcam", "ShopC", 65, "auto_pay"),
    ]
    # We'll use at least 3 products from this list
    random.shuffle(base_products)
    current_month_products = base_products[:3]  # guaranteed 3

    # Scale amounts so sum <= monthly_cap (leave some headroom)
    target_sum = min(240.0, monthly_cap * 0.8)
    raw_sum = sum(p[2] for p in current_month_products)
    scale = target_sum / raw_sum if raw_sum > 0 else 1.0

    order_idx = 0
    for i, (title, merchant, amount, action) in enumerate(current_month_products):
        # Place at fraction of elapsed time since month start
        if month_elapsed <= 0:
            captured = now
        else:
            frac = fractions[i % len(fractions)]
            captured = month_start + timedelta(seconds=month_elapsed * frac)
            if captured > now:
                captured = now
        created = captured - timedelta(minutes=random.randint(5, 60))

        scaled_amount = round(amount * scale, 2)
        order_id = f"DEMO_{now.strftime('%Y%m%d')}_{order_idx:03d}"
        order_idx += 1
        cur.execute("""
            INSERT INTO orders (order_id, user_email, title, merchant, amount, currency, action, status, capture_id, created_at, captured_at, demo)
            VALUES (?, ?, ?, ?, ?, 'USD', ?, 'captured', ?, ?, ?, 1)
        """, (
            order_id, user_email, title, merchant, scaled_amount,
            action, f"CAP_{order_id}", created.isoformat(), captured.isoformat()
        ))

    # --- Previous weeks/months: remaining ~11 orders ---
    remaining_products = [
        ("Mechanical Keyboard", "ShopC", 85, "needs_approval"),
        ("Headphones", "ShopB", 120, "needs_approval"),
        ("Bluetooth Speaker", "ShopA", 50, "auto_pay"),
        ("Gaming Mouse", "ShopB", 60, "needs_approval"),
        ("External SSD", "ShopC", 90, "auto_pay"),
        ("Laptop Stand", "ShopD", 40, "needs_approval"),
        ("Monitor Light Bar", "ShopE", 35, "auto_pay"),
        ("Keyboard Wrist Rest", "ShopA", 25, "auto_pay"),
        ("USB-C Cable", "ShopB", 15, "auto_pay"),
        ("Portable Charger", "ShopC", 40, "auto_pay"),
        ("Desk Organizer", "ShopD", 30, "needs_approval"),
    ]
    # Add the unused current month products to reach ~14 total
    all_remaining = base_products[3:] + remaining_products
    random.shuffle(all_remaining)

    for i, (title, merchant, amount, action) in enumerate(all_remaining[:11]):
        # Spread over previous 8 weeks (56 days) but not in current month
        # days_ago starts after the month boundary
        min_days_ago = max(1, int((now - month_start).days) + 1)
        days_ago = random.randint(min_days_ago, min_days_ago + 55)
        created = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        captured = created + timedelta(minutes=random.randint(5, 60))

        order_id = f"DEMO_{now.strftime('%Y%m%d')}_{order_idx:03d}"
        order_idx += 1
        cur.execute("""
            INSERT INTO orders (order_id, user_email, title, merchant, amount, currency, action, status, capture_id, created_at, captured_at, demo)
            VALUES (?, ?, ?, ?, ?, 'USD', ?, 'captured', ?, ?, ?, 1)
        """, (
            order_id, user_email, title, merchant, amount,
            action, f"CAP_{order_id}", created.isoformat(), captured.isoformat()
        ))
    conn.commit()


def seed_demo(conn: sqlite3.Connection) -> None:
    """Backward compatibility: seed demo@budgie.app"""
    seed_demo_for_user(conn, DEMO_EMAIL)


def insert_order(
    order_id: str,
    user_email: str,
    title: str,
    merchant: str,
    amount: float,
    currency: str,
    action: str,
    demo: int = 0,
) -> None:
    now = datetime.utcnow().isoformat()
    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO orders (order_id, user_email, title, merchant, amount, currency, action, status, created_at, demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'created', ?, ?)
        """, (order_id, user_email, title, merchant, amount, currency, action, now, demo))


def insert_run(
    run_id: str,
    user_email: str,
    payload: Dict[str, Any],
) -> None:
    now = datetime.utcnow().isoformat()
    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO runs (run_id, user_email, payload_json, created_at)
            VALUES (?, ?, ?, ?)
        """, (run_id, user_email, json.dumps(payload), now))


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
        row = cur.fetchone()
        if row:
            data = dict(row)
            data["payload"] = json.loads(data["payload_json"])
            return data
        return None


def update_run_payload(run_id: str, payload: Dict[str, Any]) -> None:
    """Update the stored run payload with new data (e.g., order info for idempotency)."""
    with db_cursor() as cur:
        cur.execute("""
            UPDATE runs SET payload_json = ? WHERE run_id = ?
        """, (json.dumps(payload), run_id))


def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def capture_order_db(
    order_id: str,
    capture_id: str,
    amount: float,
    currency: str,
    payer_email: Optional[str] = None,
) -> bool:
    now = datetime.utcnow().isoformat()
    with db_cursor() as cur:
        cur.execute("""
            UPDATE orders
            SET status = 'captured', capture_id = ?, captured_at = ?, amount = ?, currency = ?
            WHERE order_id = ? AND status = 'created'
        """, (capture_id, now, amount, currency, order_id))
        return cur.rowcount > 0


def get_monthly_spent(user_email: str, now: Optional[datetime] = None) -> float:
    if now is None:
        now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1).isoformat()
    next_month = now.month + 1
    next_year = now.year
    if next_month > 12:
        next_month = 1
        next_year += 1
    month_end = datetime(next_year, next_month, 1).isoformat()

    with db_cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM orders
            WHERE user_email = ? AND status = 'captured'
            AND captured_at >= ? AND captured_at < ?
        """, (user_email, month_start, month_end))
        return float(cur.fetchone()[0] or 0)


def get_spending_data(user_email: str, now: Optional[datetime] = None) -> Dict[str, Any]:
    from datetime import timedelta
    import calendar

    if now is None:
        now = datetime.utcnow()

    # On-demand demo seeding for this user (if SEED_DEMO=1 and no captured orders)
    if SEED_DEMO:
        with db_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM orders WHERE user_email = ? AND status = 'captured'", (user_email,))
            if cur.fetchone()[0] == 0:
                seed_demo_for_user(get_connection(), user_email, now=now)

    month_start = datetime(now.year, now.month, 1)
    monthly_cap = MONTHLY_CAP
    month_spent = get_monthly_spent(user_email, now=now)

    with db_cursor() as cur:
        cur.execute("""
            SELECT order_id, title, merchant, amount, currency, action, captured_at, demo
            FROM orders
            WHERE user_email = ? AND status = 'captured'
            ORDER BY captured_at DESC
            LIMIT 10
        """, (user_email,))
        orders = [dict(row) for row in cur.fetchall()]

    weekly = []
    for i in range(7, -1, -1):
        week_start = now - timedelta(weeks=i)
        year, week, _ = week_start.isocalendar()
        week_start_dt = datetime.fromisocalendar(year, week, 1)
        week_end_dt = week_start_dt + timedelta(days=7)

        with db_cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM orders
                WHERE user_email = ? AND status = 'captured'
                AND captured_at >= ? AND captured_at < ?
            """, (user_email, week_start_dt.isoformat(), week_end_dt.isoformat()))
            total = float(cur.fetchone()[0] or 0)

        weekly.append({"label": f"W{week:02d}", "total": total})

    monthly = []
    for i in range(5, -1, -1):
        month = now.month - i
        year = now.year
        if month <= 0:
            month += 12
            year -= 1

        month_start_dt = datetime(year, month, 1)
        if month == 12:
            month_end_dt = datetime(year + 1, 1, 1)
        else:
            month_end_dt = datetime(year, month + 1, 1)

        with db_cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM orders
                WHERE user_email = ? AND status = 'captured'
                AND captured_at >= ? AND captured_at < ?
            """, (user_email, month_start_dt.isoformat(), month_end_dt.isoformat()))
            total = float(cur.fetchone()[0] or 0)

        label = month_start_dt.strftime("%b")
        monthly.append({"label": label, "total": total})

    with db_cursor() as cur:
        cur.execute("""
            SELECT COUNT(*), COALESCE(SUM(amount), 0),
                   SUM(CASE WHEN action = 'auto_pay' THEN 1 ELSE 0 END) * 1.0 / COUNT(*)
            FROM orders
            WHERE user_email = ? AND status = 'captured'
        """, (user_email,))
        order_count, total_amount, auto_pay_share = cur.fetchone()
        order_count = order_count or 0
        total_amount = float(total_amount or 0)
        auto_pay_share = float(auto_pay_share or 0)

    avg_order = total_amount / order_count if order_count > 0 else 0

    return {
        "user": user_email,
        "kpis": {
            "month_total": round(month_spent, 2),
            "order_count": order_count,
            "avg_order": round(avg_order, 2),
            "auto_pay_share": round(auto_pay_share, 2),
        },
        "monthly_cap": monthly_cap,
        "weekly": weekly,
        "monthly": monthly,
        "orders": orders,
    }


def close_db():
    global _conn
    if _conn:
        _conn.close()
        _conn = None


atexit.register(close_db)
