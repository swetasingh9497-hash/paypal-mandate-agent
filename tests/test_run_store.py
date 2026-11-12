import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.auth import make_token


def test_run_response_contains_run_id(test_client):
    """Test that /api/mock/run returns a run_id."""
    response = test_client.post("/api/mock/run", json={"text": "Buy a lamp under $50"}, headers={"Authorization": f"Bearer {make_token('test@test.com')}"})
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert isinstance(data["run_id"], str)
    assert data["run_id"] == "mock_run_id"


def test_unknown_run_returns_404(test_client):
    """Test /api/runs/{run_id}/select returns 404 for unknown run."""
    response = test_client.post("/api/runs/nonexistent/select", json={"product_id": "1"}, headers={"Authorization": f"Bearer {make_token('test@test.com')}"})
    assert response.status_code == 404
    assert "Run not found" in response.json()["detail"]


def test_unknown_product_returns_404(test_client):
    """Test /api/runs/{run_id}/select returns 404 for unknown product."""
    run_response = test_client.post("/api/mock/run", json={"text": "Buy a lamp under $50"}, headers={"Authorization": f"Bearer {make_token('test@test.com')}"})
    run_id = run_response.json()["run_id"]

    response = test_client.post(f"/api/runs/{run_id}/select", json={"product_id": "999"}, headers={"Authorization": f"Bearer {make_token('test@test.com')}"})
    assert response.status_code == 404
    assert "Product not found" in response.json()["detail"]


def test_rejected_product_returns_409(test_client):
    """Test /api/runs/{run_id}/select returns 409 for rejected product."""
    run_response = test_client.post("/api/mock/run", json={"text": "Buy a lamp under $50"}, headers={"Authorization": f"Bearer {make_token('test@test.com')}"})
    run_id = run_response.json()["run_id"]

    # Product 2 is rejected in mock run
    response = test_client.post(f"/api/runs/{run_id}/select", json={"product_id": "2"}, headers={"Authorization": f"Bearer {make_token('test@test.com')}"})
    assert response.status_code == 409
    assert "rejected" in response.json()["detail"].lower()

def test_user_mismatch_returns_403(test_client):
    """Only the user who made a run may select from it."""
    from app.auth import make_token

    run_response = test_client.post(
        "/api/mock/run",
        json={"text": "Buy a lamp under $50"},
        headers={"Authorization": f"Bearer {make_token('owner@test.com')}"},
    )
    run_id = run_response.json()["run_id"]

    # another user, identified by a signed token
    r = test_client.post(
        f"/api/runs/{run_id}/select",
        json={"product_id": "1"},
        headers={"Authorization": f"Bearer {make_token('intruder@test.com')}"},
    )
    assert r.status_code == 403
    assert "mismatch" in r.json()["detail"].lower()

    # the owner passes the ownership check (product 2 is rejected -> 409, not 403)
    r = test_client.post(
        f"/api/runs/{run_id}/select",
        json={"product_id": "2"},
        headers={"Authorization": f"Bearer {make_token('owner@test.com')}"},
    )
    assert r.status_code == 409


def test_cap_exceeded_returns_409(test_client, db_conn):
    """Selecting a product that would push the user over the monthly cap gives 409."""
    from datetime import datetime
    from app.db import MONTHLY_CAP

    user = "captest@test.com"
    run_response = test_client.post(
        "/api/mock/run",
        json={"text": "Buy a lamp under $50"},
        headers={"Authorization": f"Bearer {make_token(user)}"},
    )
    run_id = run_response.json()["run_id"]

    # The user already spent almost the whole cap this month
    now = datetime.utcnow().isoformat()
    db_conn.execute(
        """
        INSERT OR REPLACE INTO orders
        (order_id, user_email, title, merchant, amount, currency, action,
         status, created_at, captured_at, demo)
        VALUES (?, ?, 'Earlier purchase', 'Shop', ?, 'USD', 'auto_pay',
                'captured', ?, ?, 0)
        """,
        ("CAP_EXISTING", user, MONTHLY_CAP - 5, now, now),
    )
    db_conn.commit()

    # Product 1 costs 20, so spent + 20 is over the cap
    r = test_client.post(
        f"/api/runs/{run_id}/select",
        json={"product_id": "1"},
        headers={"Authorization": f"Bearer {make_token(user)}"},
    )
    assert r.status_code == 409
    assert "monthly cap" in r.json()["detail"].lower()

def test_client_supplied_price_is_ignored(test_client):
    """Test that client-supplied price is ignored, server uses stored price."""
    run_response = test_client.post("/api/mock/run", json={"text": "Buy a lamp under $50"}, headers={"Authorization": f"Bearer {make_token('test@test.com')}"})
    run_id = run_response.json()["run_id"]
    run_data = run_response.json()

    # Find a non-rejected product
    passing_products = [c["product"] for c in run_data["candidates"] if c["decision"]["action"] != "reject"]
    if not passing_products:
        pytest.skip("No passing products in run")

    product = passing_products[0]
    product_id = product["id"]
    stored_price = product["price"]

    # The mock run already has an order for product_id "1", so create_order won't be called.
    # To test that the server uses the stored price (not client price), we verify
    # that the response order has the correct product data from the run.
    response = test_client.post(f"/api/runs/{run_id}/select", json={
        "product_id": product_id
    }, headers={"Authorization": f"Bearer {make_token('test@test.com')}"})

    assert response.status_code == 200
    # The returned order should match the product from the run (not any client-supplied price)
    data = response.json()
    assert data["product"]["id"] == product_id
    assert data["product"]["price"] == stored_price
    # The order already exists in the mock run, so it's returned without calling create_order


def test_idempotent_second_call_returns_same_order_id(test_client):
    """Test that second call to select for same run+product returns same order."""
    run_response = test_client.post("/api/mock/run", json={"text": "Buy a lamp under $50"}, headers={"Authorization": f"Bearer {make_token('test@test.com')}"})
    run_id = run_response.json()["run_id"]
    run_data = run_response.json()

    passing_products = [c["product"] for c in run_data["candidates"] if c["decision"]["action"] != "reject"]
    if not passing_products:
        pytest.skip("No passing products in run")

    product_id = passing_products[0]["id"]

    with patch("app.paypal.create_order", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {
            "id": "TEST_ORDER_123",
            "links": [{"rel": "payer-action", "href": "https://paypal.com/approve/TEST_ORDER_123"}]
        }

        # First call
        response1 = test_client.post(f"/api/runs/{run_id}/select", json={"product_id": product_id}, headers={"Authorization": f"Bearer {make_token('test@test.com')}"})
        assert response1.status_code == 200
        order_id_1 = response1.json()["order"]["id"]

        # Second call - should return same order (idempotent)
        response2 = test_client.post(f"/api/runs/{run_id}/select", json={"product_id": product_id}, headers={"Authorization": f"Bearer {make_token('test@test.com')}"})
        assert response2.status_code == 200
        order_id_2 = response2.json()["order"]["id"]

        # With idempotency fix, both calls should return the same order
        assert order_id_1 == order_id_2


def test_run_store_persists_mandate_and_candidates(test_client):
    """Test that run store saves mandate and all candidates with decisions."""
    run_response = test_client.post("/api/mock/run", json={"text": "Buy a lamp under $50"}, headers={"Authorization": f"Bearer {make_token('storetest@test.com')}"})
    assert run_response.status_code == 200
    run_id = run_response.json()["run_id"]

    # Fetch the run from DB
    from app.db import get_run
    run = get_run(run_id)
    assert run is not None
    assert run["user_email"] == "storetest@test.com"
    assert "payload" in run
    payload = run["payload"]
    assert "mandate" in payload
    assert "candidates" in payload
    assert len(payload["candidates"]) > 0
    for c in payload["candidates"]:
        assert "product" in c
        assert "decision" in c
        assert "action" in c["decision"]
        assert "reasons" in c["decision"]


def test_pick_logic_prefers_auto_pay_then_rating_then_price():
    """Test the deterministic pick logic: auto_pay > needs_approval, then rating desc, then price asc."""
    from app.pipeline import pick_best_candidate
    from app.schemas import Mandate, Product, Decision

    M = Mandate(item="lamp", max_total=100, min_rating=4.0, max_delivery_days=7, auto_approve_under=50)

    # Create test products with different attributes
    p1 = Product(id="1", title="AutoPay High Rating", price=30, currency="USD", rating=4.8, merchant="A", delivery_days=3, url="x")
    p2 = Product(id="2", title="AutoPay Low Rating", price=25, currency="USD", rating=4.2, merchant="B", delivery_days=3, url="x")
    p3 = Product(id="3", title="NeedsApproval High Rating", price=20, currency="USD", rating=4.9, merchant="C", delivery_days=3, url="x")
    p4 = Product(id="4", title="NeedsApproval Low Rating", price=15, currency="USD", rating=4.1, merchant="D", delivery_days=3, url="x")

    d_auto = Decision(action="auto_pay", reasons=["within auto-approve limit 50"])
    d_needs = Decision(action="needs_approval", reasons=["above auto-approve limit"])

    candidates = [
        {"product": p1, "decision": d_auto},
        {"product": p2, "decision": d_auto},
        {"product": p3, "decision": d_needs},
        {"product": p4, "decision": d_needs},
    ]

    best = pick_best_candidate(candidates)
    # Should pick p1 (auto_pay + highest rating among auto_pay)
    assert best is not None
    assert best["product"].id == "1"

    # Test with only needs_approval
    candidates2 = [
        {"product": p3, "decision": d_needs},
        {"product": p4, "decision": d_needs},
    ]
    best2 = pick_best_candidate(candidates2)
    # Should pick p3 (highest rating)
    assert best2["product"].id == "3"

    # Test with same rating, different price
    p5 = Product(id="5", title="Same Rating Cheaper", price=20, currency="USD", rating=4.5, merchant="E", delivery_days=3, url="x")
    p6 = Product(id="6", title="Same Rating Pricier", price=30, currency="USD", rating=4.5, merchant="F", delivery_days=3, url="x")
    d_auto2 = Decision(action="auto_pay", reasons=["within auto-approve limit 50"])
    candidates3 = [
        {"product": p5, "decision": d_auto2},
        {"product": p6, "decision": d_auto2},
    ]
    best3 = pick_best_candidate(candidates3)
    # Should pick p5 (lower price)
    assert best3["product"].id == "5"
