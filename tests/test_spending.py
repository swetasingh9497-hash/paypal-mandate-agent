import os
import tempfile
import sqlite3
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

# Set test database path before importing app
test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
test_db.close()
os.environ["DB_PATH"] = test_db.name
os.environ["MONTHLY_CAP"] = "500"
os.environ["SEED_DEMO"] = "0"

from app.main import app
from app.db import insert_order, get_monthly_spent, get_spending_data, close_db, get_connection, set_test_connection, SEED_DEMO

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
    conn.execute("DELETE FROM orders")
    conn.commit()

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
    conn.execute("DELETE FROM orders")
    conn.commit()

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
    conn.execute("DELETE FROM orders")
    conn.commit()

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
    conn.execute("DELETE FROM orders")
    conn.commit()

    insert_order("ORD_CAPTURED", "user@test.com", "Item", "Shop", 50, "USD", "auto_pay")
    conn.execute("UPDATE orders SET status = 'captured', captured_at = ? WHERE order_id = ?", (datetime.utcnow().isoformat(), "ORD_CAPTURED"))
    conn.commit()

    response = client.post("/api/orders/ORD_CAPTURED/capture")
    assert response.status_code == 409
    assert "already captured" in response.json()["detail"].lower()


def test_spending_api_structure():
    """Test /api/spending returns correct structure"""
    conn = get_test_conn()
    conn.execute("DELETE FROM orders")
    conn.commit()

    user = "api@test.com"
    insert_order("ORD_API", user, "Test Item", "Test Shop", 75, "USD", "auto_pay")
    conn.execute("UPDATE orders SET status = 'captured', captured_at = ? WHERE order_id = ?", (datetime.utcnow().isoformat(), "ORD_API"))
    conn.commit()

    response = client.get(f"/api/spending?user={user}")
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


def test_seed_demo_on_demand_for_user_with_no_orders():
    """Test that SEED_DEMO=1 seeds ~14 demo orders for a user with zero captured orders."""
    # Enable SEED_DEMO for this test
    os.environ["SEED_DEMO"] = "1"
    # Need to re-initialize the app/db with the new setting
    from app.db import close_db, get_connection
    close_db()
    # Re-import to pick up the new env var
    import importlib
    import app.db
    importlib.reload(app.db)
    
    conn = get_test_conn()
    conn.execute("DELETE FROM orders")
    conn.commit()

    user = "seeded@user.com"
    # User has NO captured orders
    data = get_spending_data(user)
    
    # Should now have demo orders
    assert data["kpis"]["order_count"] >= 14
    assert data["kpis"]["month_total"] > 0
    # All seeded orders should have demo=1
    for order in data["orders"]:
        assert order["demo"] == 1
    # Check mix of actions
    actions = [o["action"] for o in data["orders"]]
    assert "auto_pay" in actions
    assert "needs_approval" in actions
    
    os.environ["SEED_DEMO"] = "0"
    close_db()


def test_seed_demo_skips_user_with_existing_orders():
    """Test that SEED_DEMO=1 does NOT seed for a user who already has captured orders."""
    os.environ["SEED_DEMO"] = "1"
    from app.db import close_db
    close_db()
    import importlib
    import app.db
    importlib.reload(app.db)
    
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
    
    os.environ["SEED_DEMO"] = "0"
    close_db()
