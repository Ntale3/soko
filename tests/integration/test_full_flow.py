"""
End-to-end integration tests for the Soko marketplace backend.

These tests verify that all services are up and communicating correctly —
HTTP calls between services, RabbitMQ event propagation, and DB writes.

Run with:
  pip install pytest httpx
  pytest tests/integration/ -v
"""

import time
import httpx
import pytest
from helpers import BASE_URLS, auth_headers, register_and_login


# ─────────────────────────────────────────────────────────────────────────────
# 1. HEALTH CHECKS — all five services must be reachable
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("service", BASE_URLS.keys())
def test_service_health(service):
    resp = httpx.get(f"{BASE_URLS[service]}/health", timeout=5)
    assert resp.status_code == 200, f"{service} health check failed"
    body = resp.json()
    assert body["status"] == "ok", f"{service} reported unhealthy: {body}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. AUTH SERVICE — register + login
# ─────────────────────────────────────────────────────────────────────────────

def test_auth_register_and_login(farmer_token):
    """farmer_token fixture already did register+login — just assert it's a string."""
    assert isinstance(farmer_token, str) and len(farmer_token) > 20


def test_auth_me(farmer_token):
    resp = httpx.get(
        f"{BASE_URLS['auth']}/auth/me",
        headers=auth_headers(farmer_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "farmer"
    assert body["email"] == "farmer_test@soko.io"


def test_auth_rejects_bad_token():
    resp = httpx.get(
        f"{BASE_URLS['auth']}/auth/me",
        headers={"Authorization": "Bearer totally_fake_token"},
    )
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 3. FARMER SERVICE — profile creation
# ─────────────────────────────────────────────────────────────────────────────

def test_farmer_profile_exists(farmer_token, farmer_profile):
    resp = httpx.get(
        f"{BASE_URLS['farmer']}/farmers/profile",
        headers=auth_headers(farmer_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["district"] == "Kampala"


def test_farmer_requires_auth():
    resp = httpx.get(f"{BASE_URLS['farmer']}/farmers/profile")
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 4. PRODUCE SERVICE — listing creation + public search
# ─────────────────────────────────────────────────────────────────────────────

def test_produce_listing_created(produce_listing):
    assert produce_listing["name"] == "Test Tomatoes"
    assert produce_listing["quantity"] == 100.0
    assert produce_listing["is_available"] is True


def test_produce_public_search(produce_listing):
    resp = httpx.get(
        f"{BASE_URLS['produce']}/produce/",
        params={"name": "Tomatoes"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    names = [r["name"] for r in body["results"]]
    assert any("Tomato" in n for n in names)


def test_produce_get_by_id(produce_listing):
    pid = produce_listing["id"]
    resp = httpx.get(f"{BASE_URLS['produce']}/produce/{pid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == pid


def test_produce_farmer_requires_auth():
    resp = httpx.post(f"{BASE_URLS['produce']}/produce/", json={})
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 5. BUYER SERVICE — order placement (tests HTTP call to produce service)
# ─────────────────────────────────────────────────────────────────────────────

def test_order_placed(placed_order, produce_listing):
    assert placed_order["produce_id"] == produce_listing["id"]
    assert placed_order["quantity_kg"] == 5.0
    assert placed_order["status"] == "pending"
    # Total = 5kg × 2500 = 12500
    assert placed_order["total_price"] == pytest.approx(12500.0)


def test_stock_reduced_after_order(produce_listing):
    """
    Verify the buyer service correctly called Produce service to reduce stock.
    100kg initial − 5kg ordered = 95kg remaining.
    """
    pid = produce_listing["id"]
    resp = httpx.get(f"{BASE_URLS['produce']}/produce/{pid}")
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["quantity"] == pytest.approx(95.0), (
        f"Expected 95kg remaining, got {updated['quantity']}kg"
    )


def test_buyer_can_list_orders(buyer_token, placed_order):
    resp = httpx.get(
        f"{BASE_URLS['buyer']}/orders/",
        headers=auth_headers(buyer_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    order_ids = [o["id"] for o in body["results"]]
    assert placed_order["id"] in order_ids


def test_buyer_cannot_order_without_profile():
    """A fresh user with no buyer profile should get 404."""

    token = register_and_login(
        email="noprofile_test@soko.io",
        password="nopassword123",
        full_name="No Profile",
        role="buyer",
    )
    resp = httpx.post(
        f"{BASE_URLS['buyer']}/orders/",
        json={"produce_id": 1, "quantity_kg": 1.0},
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


def test_order_rejects_excess_quantity(buyer_token, produce_listing):
    """Ordering more than available stock should return 400."""
    resp = httpx.post(
        f"{BASE_URLS['buyer']}/orders/",
        json={"produce_id": produce_listing["id"], "quantity_kg": 99999.0},
        headers=auth_headers(buyer_token),
    )
    assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# 6. BUYER SERVICE — reviews
# ─────────────────────────────────────────────────────────────────────────────

def test_review_requires_completed_order(buyer_token, placed_order):
    """
    Reviews require a 'completed' order status.
    Our test order is still 'pending', so this should fail with 400.
    """
    resp = httpx.post(
        f"{BASE_URLS['buyer']}/reviews/{placed_order['id']}",
        json={"stars": 5, "comment": "Great produce!"},
        headers=auth_headers(buyer_token),
    )
    assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# 7. RECOMMENDATION SERVICE — event propagation via RabbitMQ
# ─────────────────────────────────────────────────────────────────────────────

def test_recommendation_produce_score_endpoint(produce_listing):
    """
    The produce.listed event should have been consumed and stored.
    Score endpoint should return without error even if no reviews yet.
    """
    pid = produce_listing["id"]
    resp = httpx.get(f"{BASE_URLS['recommendation']}/recommendations/produce/{pid}/score")
    assert resp.status_code == 200
    body = resp.json()
    assert body["produce_id"] == pid
    assert body["total_reviews"] >= 0


def test_recommendation_produce_listed_event_consumed(produce_listing):
    """
    After the farmer listed produce, the produce.listed event should have
    been consumed by the recommendation service and stored as a ProduceSummary.
    We verify indirectly: GET /recommendations/ returns results that include
    our test produce (since no orders yet → it won't be excluded).
    Allow up to 5 seconds for async propagation.
    """


    # Fresh buyer so they have no order history — should get recommendations
    token = register_and_login(
        email="fresh_buyer@soko.io",
        password="freshpass123",
        full_name="Fresh Buyer",
        role="buyer",
    )

    deadline = time.time() + 15
    found = False
    while time.time() < deadline:
        resp = httpx.get(
            f"{BASE_URLS['recommendation']}/recommendations/",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, f"Recommendations endpoint failed: {resp.text}"
        body = resp.json()
        produce_ids = [r["produce_id"] for r in body["results"]]
        if produce_listing["id"] in produce_ids:
            found = True
            break
        time.sleep(0.5)

    assert found, (
        "Produce listing not found in recommendations after 5s — "
        "produce.listed event may not have been consumed."
    )


def test_recommendation_order_event_consumed(buyer_token, placed_order, produce_listing):
    """
    After placing an order, order.placed event should be consumed.
    The ordered produce should be EXCLUDED from that buyer's recommendations.
    Allow up to 5 seconds for async propagation.
    """
    deadline = time.time() + 15
    excluded = False
    while time.time() < deadline:
        resp = httpx.get(
            f"{BASE_URLS['recommendation']}/recommendations/",
            headers=auth_headers(buyer_token),
        )
        assert resp.status_code == 200
        body = resp.json()
        produce_ids = [r["produce_id"] for r in body["results"]]
        if produce_listing["id"] not in produce_ids:
            excluded = True
            break
        time.sleep(0.5)

    assert excluded, (
        f"Produce {produce_listing['id']} still appears in recommendations after order — "
        "order.placed event may not have been consumed within 5s."
    )


def test_recommendation_requires_auth():
    resp = httpx.get(f"{BASE_URLS['recommendation']}/recommendations/")
    assert resp.status_code == 403  # HTTPBearer returns 403 when header missing
