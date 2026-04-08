"""
Redis caching integration tests.

Verifies that Redis caching is working correctly for:
  - Produce price predictions  (produce service  → Redis DB 1)
  - Recommendations per buyer  (recommendation service → Redis DB 0)
  - Produce quality scores     (recommendation service → Redis DB 0)

Each test group covers three properties:
  1. Cache population  — a successful HTTP call writes to Redis
  2. Cache hit         — a second call returns identical data
  3. Cache invalidation — the right mutation busts the cache

Prerequisites: all services + Redis running via `docker compose up --build`
Run with:
  pip install pytest httpx redis
  pytest tests/integration/ -v
"""

import time
import uuid
import httpx
import pytest
import redis as redis_lib
from helpers import BASE_URLS, auth_headers, register_and_login

# Direct Redis clients — match the DB numbers assigned in docker-compose
_REDIS_RECS   = redis_lib.Redis(host="localhost", port=6379, db=0, decode_responses=True)
_REDIS_PRICES = redis_lib.Redis(host="localhost", port=6379, db=1, decode_responses=True)


# ── Connectivity ──────────────────────────────────────────────────────

def test_redis_reachable():
    """Both Redis databases must respond to PING."""
    assert _REDIS_RECS.ping(),   "Redis DB 0 (recommendations) not reachable"
    assert _REDIS_PRICES.ping(), "Redis DB 1 (produce prices) not reachable"


# ── Price predictions caching (produce service, Redis DB 1) ───────────

def test_price_predictions_populates_cache(produce_listing):
    """
    After calling /produce/prices/predictions the result must be stored
    in Redis DB 1 under key `predictions:None:None` with a TTL ≤ 600 s.
    """
    # Ensure a clean slate so this isn't a residual hit from a prior test
    _REDIS_PRICES.delete("predictions:all:all")

    resp = httpx.get(f"{BASE_URLS['produce']}/produce/prices/predictions")
    assert resp.status_code == 200

    assert _REDIS_PRICES.exists("predictions:all:all"), (
        "Price prediction result was not stored in Redis after endpoint call"
    )
    ttl = _REDIS_PRICES.ttl("predictions:all:all")
    assert 0 < ttl <= 600, f"Unexpected TTL: {ttl}"


def test_price_predictions_cache_hit_is_consistent(produce_listing):
    """Two consecutive calls must return identical JSON."""
    first  = httpx.get(f"{BASE_URLS['produce']}/produce/prices/predictions").json()
    second = httpx.get(f"{BASE_URLS['produce']}/produce/prices/predictions").json()
    assert first == second


def test_price_predictions_cache_invalidated_after_new_listing(farmer_token):
    """
    Creating a new listing must bust all prediction cache keys.
    The updated predictions must reflect the new listing.
    """
    # Start with a warm cache
    _REDIS_PRICES.delete("predictions:None:None")
    baseline_resp = httpx.get(f"{BASE_URLS['produce']}/produce/prices/predictions")
    assert baseline_resp.status_code == 200
    baseline_counts = {
        r["category"]: r["listing_count"]
        for r in baseline_resp.json()["results"]
    }

    # Create a new listing in the "other" category
    new_resp = httpx.post(
        f"{BASE_URLS['produce']}/produce/",
        json={
            "name": f"redis_invalidation_test_{uuid.uuid4().hex[:6]}",
            "category": "other",
            "quantity": 5.0,
            "price_per_unit": 3500.0,
            "district": "Wakiso",
            "unit": "kg",
        },
        headers=auth_headers(farmer_token),
    )
    assert new_resp.status_code == 201, f"Could not create listing: {new_resp.text}"

    # The old cache entry must be gone (invalidate_predictions deletes all predictions:* keys)
    assert not _REDIS_PRICES.exists("predictions:all:all"), (
        "Prediction cache was not invalidated after new listing was created"
    )

    # Fresh call must return updated counts
    updated_counts = {
        r["category"]: r["listing_count"]
        for r in httpx.get(f"{BASE_URLS['produce']}/produce/prices/predictions").json()["results"]
    }
    other_before = baseline_counts.get("other", 0)
    other_after  = updated_counts.get("other", 0)
    assert other_after > other_before, (
        f"Expected 'other' listing_count to increase after new listing "
        f"({other_before} → {other_after})"
    )


def test_price_predictions_category_filter_cached_separately(farmer_token):
    """
    A filtered call (e.g. ?category=vegetables) must be cached under its own key
    and not return data for other categories.
    """
    resp = httpx.get(
        f"{BASE_URLS['produce']}/produce/prices/predictions",
        params={"category": "vegetables"},
    )
    assert resp.status_code == 200
    body = resp.json()

    # The filtered response only contains the requested category (or is empty)
    for item in body["results"]:
        assert item["category"] == "vegetables", (
            f"Unexpected category '{item['category']}' in filtered predictions response"
        )

    # A separate key must exist in Redis for this filter combo.
    # Pattern scan so the test is resilient to enum serialisation differences
    # across Python versions (key may be "predictions:vegetables:all" or
    # "predictions:ProduceCategory.vegetables:all" depending on runtime).
    vegetable_keys = _REDIS_PRICES.keys("predictions:*vegetables*")
    assert vegetable_keys, (
        f"No vegetables prediction key found in Redis DB 1. "
        f"Existing keys: {_REDIS_PRICES.keys('predictions:*')}"
    )


# ── Recommendation caching (recommendation service, Redis DB 0) ────────

def test_recommendations_populates_cache(buyer_token):
    """
    After calling /recommendations/ the result must be stored in Redis DB 0
    under key `recs:{buyer_id}` with a TTL ≤ 300 s.
    """
    resp = httpx.get(
        f"{BASE_URLS['recommendation']}/recommendations/",
        headers=auth_headers(buyer_token),
    )
    assert resp.status_code == 200
    buyer_id = resp.json()["buyer_id"]

    # Delete first so we know the next call writes a fresh entry
    _REDIS_RECS.delete(f"recs:{buyer_id}")
    httpx.get(
        f"{BASE_URLS['recommendation']}/recommendations/",
        headers=auth_headers(buyer_token),
    )

    assert _REDIS_RECS.exists(f"recs:{buyer_id}"), (
        f"Recommendations not cached in Redis under recs:{buyer_id}"
    )
    ttl = _REDIS_RECS.ttl(f"recs:{buyer_id}")
    assert 0 < ttl <= 300, f"Unexpected TTL: {ttl}"


def test_recommendations_cache_hit_is_consistent(buyer_token):
    """Two consecutive calls return the same produce IDs."""
    headers = auth_headers(buyer_token)
    first  = httpx.get(f"{BASE_URLS['recommendation']}/recommendations/", headers=headers).json()
    second = httpx.get(f"{BASE_URLS['recommendation']}/recommendations/", headers=headers).json()

    assert first["buyer_id"] == second["buyer_id"]
    assert first["total"]    == second["total"]
    assert {r["produce_id"] for r in first["results"]} == {r["produce_id"] for r in second["results"]}


def test_recommendations_cache_invalidated_after_order(farmer_token, buyer_token, produce_listing):
    """
    Placing an order publishes order.placed → messaging handler calls
    invalidate_recommendations(buyer_id) → Redis key is deleted.
    Verify the key disappears within 10 s of the order being placed.
    """
    headers   = auth_headers(buyer_token)

    # Ensure the cache key exists first
    resp      = httpx.get(f"{BASE_URLS['recommendation']}/recommendations/", headers=headers)
    buyer_id  = resp.json()["buyer_id"]
    cache_key = f"recs:{buyer_id}"
    assert _REDIS_RECS.exists(cache_key), "Cache key not present before order — cannot test invalidation"

    # Create a disposable listing so we don't exhaust the shared produce_listing stock
    listing = httpx.post(
        f"{BASE_URLS['produce']}/produce/",
        json={
            "name": f"recs_invalidation_{uuid.uuid4().hex[:6]}",
            "category": "dairy",
            "quantity": 20.0,
            "price_per_unit": 4000.0,
            "district": "Jinja",
            "unit": "kg",
        },
        headers=auth_headers(farmer_token),
    )
    assert listing.status_code == 201
    new_produce_id = listing.json()["id"]

    # Wait for produce.listed event so the listing appears in candidates
    deadline = time.time() + 15
    while time.time() < deadline:
        ids = {r["produce_id"] for r in httpx.get(
            f"{BASE_URLS['recommendation']}/recommendations/?limit=100", headers=headers
        ).json()["results"]}
        if new_produce_id in ids:
            break
        time.sleep(0.5)

    # Place the order
    order = httpx.post(
        f"{BASE_URLS['buyer']}/orders/",
        json={"produce_id": new_produce_id, "quantity_kg": 1.0},
        headers=headers,
    )
    assert order.status_code == 201

    # Cache key must be deleted by the event handler within 10 s
    deadline = time.time() + 10
    invalidated = False
    while time.time() < deadline:
        if not _REDIS_RECS.exists(cache_key):
            invalidated = True
            break
        time.sleep(0.3)

    assert invalidated, (
        f"Redis key {cache_key} was not deleted within 10 s after order.placed event"
    )


# ── Produce score caching (recommendation service, Redis DB 0) ─────────

def test_produce_score_populates_cache(produce_listing):
    """
    Calling /recommendations/produce/{id}/score must store the result under
    `score:{produce_id}` in Redis DB 0 with a TTL ≤ 600 s.
    """
    pid = produce_listing["id"]
    _REDIS_RECS.delete(f"score:{pid}")

    resp = httpx.get(f"{BASE_URLS['recommendation']}/recommendations/produce/{pid}/score")
    assert resp.status_code == 200

    assert _REDIS_RECS.exists(f"score:{pid}"), (
        f"Score not cached in Redis under score:{pid}"
    )
    ttl = _REDIS_RECS.ttl(f"score:{pid}")
    assert 0 < ttl <= 600, f"Unexpected TTL: {ttl}"


def test_produce_score_cache_hit_is_consistent(produce_listing):
    """Two calls to the score endpoint return identical data."""
    pid  = produce_listing["id"]
    url  = f"{BASE_URLS['recommendation']}/recommendations/produce/{pid}/score"
    assert httpx.get(url).json() == httpx.get(url).json()


def test_produce_score_cache_invalidated_after_quality_event(
    farmer_token, buyer_token, produce_listing
):
    """
    Submitting a review (quality.scored event) must delete score:{produce_id}
    from Redis DB 0 so the next read reflects the updated rating.

    This test drives an order all the way to 'completed' so a review is allowed.
    """
    headers_buyer  = auth_headers(buyer_token)
    headers_farmer = auth_headers(farmer_token)

    # Create a fresh listing and order, then complete it
    listing = httpx.post(
        f"{BASE_URLS['produce']}/produce/",
        json={
            "name": f"score_invalidation_{uuid.uuid4().hex[:6]}",
            "category": "fruits",
            "quantity": 30.0,
            "price_per_unit": 2000.0,
            "district": "Kampala",
            "unit": "kg",
        },
        headers=headers_farmer,
    )
    assert listing.status_code == 201
    pid = listing.json()["id"]

    order = httpx.post(
        f"{BASE_URLS['buyer']}/orders/",
        json={"produce_id": pid, "quantity_kg": 1.0},
        headers=headers_buyer,
    )
    assert order.status_code == 201
    oid = order.json()["id"]

    # Farmer confirms then completes the order
    for status in ("confirmed", "completed"):
        r = httpx.patch(
            f"{BASE_URLS['buyer']}/farmer/orders/{oid}/status?new_status={status}",
            headers=headers_farmer,
        )
        assert r.status_code == 200, f"Could not set order status to {status}: {r.text}"

    # Warm the score cache
    httpx.get(f"{BASE_URLS['recommendation']}/recommendations/produce/{pid}/score")
    assert _REDIS_RECS.exists(f"score:{pid}"), "Score cache not populated before review"

    # Submit a review — triggers quality.scored event
    review = httpx.post(
        f"{BASE_URLS['buyer']}/reviews/{oid}",
        json={"stars": 4, "comment": "Good produce for testing"},
        headers=headers_buyer,
    )
    assert review.status_code == 201, f"Review submission failed: {review.text}"

    # score:{pid} must be deleted by the event handler within 45 s
    deadline = time.time() + 45
    invalidated = False
    while time.time() < deadline:
        if not _REDIS_RECS.exists(f"score:{pid}"):
            invalidated = True
            break
        time.sleep(0.3)

    assert invalidated, (
        f"Redis key score:{pid} was not deleted within 45 s after quality.scored event"
    )
