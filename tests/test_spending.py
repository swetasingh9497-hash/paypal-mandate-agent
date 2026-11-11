import os
import tempfile
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest

# Set test database path before importing app
test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
test_db.close()
os.environ["DB_PATH"] = test_db.name
os.environ["MONTHLY_CAP"] = "500"
os.environ["SEED_DEMO"] = "0"

from app.main import app
from app.db import insert_order, get_monthly_spent, get_spending_data, close_db, get_connection, set_test_connection, SEED_DEMO, MONTHLY_CAP

client = TestClient(app)


def get_test_conn():
    """Create and return a fresh test connection."""
    conn = sqlite3.connect(test_db.name, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    set_test_connection(conn)
    return conn


def setup_module():
    # Ensure clean database
    conn = get_test_conn()
    conn.execute("DELETE FROM orders")
    conn.commit()


def teardown_module():
    close_db()
    try:
        os.unlink(test_db.name)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def clear_orders():
    """Clear test data before each test."""
    conn = get_test_conn()
    conn.execute("DELETE FROM orders")
    conn.commit()
    yield
    conn.execute("DELETE FROM orders")
    conn.commit()


def test_cap_boundary_passes():
    """Test that spend + price == cap passes (needs_approval, not reject)"""
    from app.schemas import Mandate, Product
    from app.rules import evaluate

    M = Mandate(item="desk lamp", max_total=60, min_rating=4.0,
                max_delivery_days=7, auto_approve_under=25)
    p = Product(id="1", title="Test", price=50, currency="USD",
                rating=4.5, merchant="Shop", delivery_days=3, url="x")
    result = evaluate(M, p, 450, 500)
    assert result.action == "needs_approval"


def test_cap_exceeded_rejects():
    """Test that spend + price > cap rejects"""
    from app.schemas import Mandate, Product
    from app.rules import evaluate

    M = Mandate(item="desk lamp", max_total=60, min_rating=4.0,
                max_delivery_days=7, auto_approve_under=25)
    p = Product(id="1", title="Test", price=51, currency="USD",
                rating=4.5, merchant="Shop", delivery_days=3, url="x")
    result = evaluate(M, p, 450, 500)
    assert result.action == "reject"
    assert any("monthly cap" in r.lower() for r in result.reasons)


def test_spending_zero_fill_weeks():
    """Test weekly aggregation zero-fills gaps"""
    conn = get_test_conn()
    user = "test@user.com"
    now = datetime.utcnow()

    # Insert order only in week 1 (7 weeks ago)
    week_ago = now - timedelta(weeks=7)
    insert_order("ORD_1", user, "Item", "Shop", 100, "USD", "auto_pay")
    # Manually update status and captured_at
    conn.execute("UPDATE orders SET status = 'captured', captured_at = ? WHERE order_id = ?", (week_ago.isoformat(), "ORD_1"))
    conn.commit()

    data = get_spending_data(user)
    weekly = data["weekly"]

    # Should have 8 weeks
    assert len(weekly) == 8

    # Find the week with the order
    year, week, _ = week_ago.isocalendar()
    target_label = f"W{week:02d}"

    found = False
    for w in weekly:
        if w["label"] == target_label:
            assert w["total"] == 100
            found = True
        else:
            assert w["total"] == 0
    assert found


def test_spending_zero_fill_months():
    """Test monthly aggregation zero-fills gaps"""
    conn = get_test_conn()
    user = "test2@user.com"
    now = datetime.utcnow()

    # Insert order 5 months ago
    five_months_ago = datetime(now.year, now.month - 5, 15) if now.month > 5 else datetime(now.year - 1, now.month + 7, 15)
    insert_order("ORD_2", user, "Item", "Shop", 200, "USD", "auto_pay")
    conn.execute("UPDATE orders SET status = 'captured', captured_at = ? WHERE order_id = ?", (five_months_ago.isoformat(), "ORD_2"))
    conn.commit()

    data = get_spending_data(user)
    monthly = data["monthly"]

    # Should have 6 months
    assert len(monthly) == 6

    # Find the month with the order
    target_label = five_months_ago.strftime("%b")

    found = False
    for m in monthly:
        if m["label"] == target_label:
            assert m["total"] == 200
            found = True
        else:
            assert m["total"] == 0
    assert found


def test_user_isolation():
    """Test that one user's orders never appear for another"""
    conn = get_test_conn()
    insert_order("ORD_A", "userA@test.com", "Item A", "Shop", 100, "USD", "auto_pay")
    insert_order("ORD_B", "userB@test.com", "Item B", "Shop", 200, "USD", "auto_pay")
    # Mark as captured
    conn.execute("UPDATE orders SET status = 'captured', captured_at = ?", (datetime.utcnow().isoformat(),))
    conn.commit()

    data_a = get_spending_data("userA@test.com")
    data_b = get_spending_data("userB@test.com")

    assert len(data_a["orders"]) == 1
    assert data_a["orders"][0]["order_id"] == "ORD_A"
    assert data_a["kpis"]["month_total"] == 100

    assert len(data_b["orders"]) == 1
    assert data_b["orders"][0]["order_id"] == "ORD_B"
    assert data_b["kpis"]["month_total"] == 200


def test_capture_unknown_order_returns_404():
    """Test capture of unknown order returns 404"""
    response = client.post("/api/orders/UNKNOWN_ORDER/capture")
    assert response.status_code == 404


def test_capture_already_captured_returns_409():
    """Test capture of already captured order returns 409"""
    conn = get_test_conn()
    insert_order("ORD_CAPTURED", "user@test.com", "Item", "Shop", 50, "USD", "auto_pay")
    conn.execute("UPDATE orders SET status = 'captured', captured_at = ? WHERE order_id = ?", (datetime.utcnow().isoformat(), "ORD_CAPTURED"))
    conn.commit()

    response = client.post("/api/orders/ORD_CAPTURED/capture")
    assert response.status_code == 409
    assert "already captured" in response.json()["detail"].lower()


def test_spending_api_structure():
    """Test /api/spending returns correct structure"""
    conn = get_test_conn()
    user = "api@test.com"

    insert_order("ORD_API", user, "Test Item", "Test Shop", 75, "USD", "auto_pay")
    conn.execute("UPDATE orders SET status = 'captured', captured_at = ? WHERE order_id = ?", (datetime.utcnow().isoformat(), "ORD_API"))
    conn.commit()
    response = client.get("/api/spending", params={"user": user})

    assert response.status_code == 200

    data = response.json()
    assert "user" in data
    assert "kpis" in data
    assert "monthly_cap" in data
    assert "weekly" in data
    assert "monthly" in data
    assert "orders" in data

    assert data["kpis"]["month_total"] == 75
    assert data["kpis"]["order_count"] == 1
    assert data["kpis"]["avg_order"] == 75
    assert data["kpis"]["auto_pay_share"] == 1.0

    assert len(data["weekly"]) == 8
    assert len(data["monthly"]) == 6
    assert len(data["orders"]) == 1
    assert data["orders"][0]["title"] == "Test Item"


def test_seed_demo_on_demand_for_user_with_no_orders(monkeypatch):
    """Test that SEED_DEMO=1 seeds ~14 demo orders for a user with zero captured orders."""
    monkeypatch.setenv("SEED_DEMO", "1")
    # Reset the module-level SEED_DEMO flag
    import app.db as db_module
    db_module.SEED_DEMO = True

    conn = get_test_conn()
    conn.execute("DELETE FROM orders")
    conn.commit()

    user = "seeded@user.com"
    # User has NO captured orders
    data = get_spending_data(user)

    # Should now have demo orders
    assert data["kpis"]["order_count"] >= 14
    assert data["kpis"]["month_total"] > 0
    assert data["kpis"]["month_total"] <= MONTHLY_CAP
    # All seeded orders should have demo=1
    for order in data["orders"]:
        assert order["demo"] == 1
    # Check mix of actions
    actions = [o["action"] for o in data["orders"]]
    assert "auto_pay" in actions
    assert "needs_approval" in actions


def test_seed_demo_skips_user_with_existing_orders(monkeypatch):
    """Test that SEED_DEMO=1 does NOT seed for a user who already has captured orders."""
    monkeypatch.setenv("SEED_DEMO", "1")
    import app.db as db_module
    db_module.SEED_DEMO = True

    conn = get_test_conn()
    conn.execute("DELETE FROM orders")
    conn.commit()

    user = "existing@user.com"
    # User already has a real captured order
    insert_order("ORD_REAL", user, "Real Item", "Shop", 100, "USD", "auto_pay")
    conn.execute("UPDATE orders SET status = 'captured', captured_at = ? WHERE order_id = ?", (datetime.utcnow().isoformat(), "ORD_REAL"))
    conn.commit()

    data = get_spending_data(user)

    # Should NOT have demo orders (only the real one)
    assert data["kpis"]["order_count"] == 1
    assert data["kpis"]["month_total"] == 100
    # The order should not be demo
    assert data["orders"][0]["demo"] == 0
    assert data["orders"][0]["order_id"] == "ORD_REAL"


def test_seed_demo_current_month_on_2nd_of_month(monkeypatch):
    """Test that seeding on the 2nd of a month still creates orders in current month."""
    monkeypatch.setenv("SEED_DEMO", "1")
    import app.db as db_module
    db_module.SEED_DEMO = True

    # Freeze "today" to the 2nd day of the month at 10:00 UTC
    frozen_now = datetime(2026, 3, 2, 10, 0, 0)

    conn = get_test_conn()
    conn.execute("DELETE FROM orders")
    conn.commit()

    user = "frozen@user.com"
    # Call seeder directly with frozen time
    db_module.seed_demo_for_user(conn, user, now=frozen_now)
    # Pass frozen_now to get_spending_data so month filter uses the same time
    data = get_spending_data(user, now=frozen_now)

    # Should have demo orders with some in current month (March 2026)
    assert data["kpis"]["order_count"] >= 14
    assert data["kpis"]["month_total"] > 0
    assert data["kpis"]["month_total"] <= MONTHLY_CAP
    # Verify at least 3 orders have captured_at in March 2026 (between 1st and now)
    march_orders = [o for o in data["orders"] if o["captured_at"].startswith("2026-03")]
    assert len(march_orders) >= 3
    # All march orders should be between 1st and now (not future)
    for o in march_orders:
        captured = datetime.fromisoformat(o["captured_at"])
        assert captured >= datetime(2026, 3, 1)
        assert captured <= frozen_now
    # No order in the future
    for o in data["orders"]:
        captured = datetime.fromisoformat(o["captured_at"])
        assert captured <= frozen_now