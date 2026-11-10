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
DEMO_EMAIL = "demo@mandate.app"

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


def seed_demo_for_user(conn: sqlite3.Connection, user_email: str) -> None:
    """Seed ~14 captured demo orders for a specific user if they have none."""
    cur = conn.cursor()
    # Check if user already has ANY captured orders (demo or real)
    cur.execute("SELECT COUNT(*) FROM orders WHERE user_email = ? AND status = 'captured'", (user_email,))
    if cur.fetchone()[0] > 0:
        return

    import random
    from datetime import timedelta

    base_date = datetime.utcnow()
    products = [
        ("Basic LED Lamp", "ShopA", 20, "auto_pay"),
        ("Wireless Mouse", "ShopB", 35, "needs_approval"),
        ("Mechanical Keyboard", "ShopC", 85, "needs_approval"),
        ("USB-C Hub", "ShopD", 45, "auto_pay"),
        ("Monitor Stand", "ShopE", 55, "needs_approval"),
        ("Desk Lamp", "ShopA", 30, "auto_pay"),
        ("Headphones", "ShopB", 120, "needs_approval"),
        ("Webcam", "ShopC", 65, "auto_pay"),
    ]

    for i in range(14):
        product = products[i % len(products)]
        days_ago = random.randint(1, 56)
        created = base_date - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        captured = created + timedelta(minutes=random.randint(5, 60))

        order_id = f"DEMO_{base_date.strftime('%Y%m%d')}_{i:03d}"
        cur.execute("""
            INSERT INTO orders (order_id, user_email, title, merchant, amount, currency, action, status, capture_id, created_at, captured_at, demo)
            VALUES (?, ?, ?, ?, ?, 'USD', ?, 'captured', ?, ?, ?, 1)
        """, (
            order_id, user_email, product[0], product[1], product[2],
            product[3], f"CAP_{order_id}", created.isoformat(), captured.isoformat()
        ))
    conn.commit()


def seed_demo(conn: sqlite3.Connection) -> None:
    """Backward compatibility: seed demo@mandate.app"""
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


def get_monthly_spent(user_email: str) -> float:
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


def get_spending_data(user_email: str) -> Dict[str, Any]:
    from datetime import timedelta
    import calendar

    # On-demand demo seeding for this user (if SEED_DEMO=1 and no captured orders)
    if SEED_DEMO:
        with db_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM orders WHERE user_email = ? AND status = 'captured'", (user_email,))
            if cur.fetchone()[0] == 0:
                seed_demo_for_user(get_connection(), user_email)

    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    monthly_cap = MONTHLY_CAP
    month_spent = get_monthly_spent(user_email)

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
