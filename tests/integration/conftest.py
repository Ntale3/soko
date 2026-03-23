"""
Shared fixtures for the Soko integration test suite.

Prerequisites:
  - All services running via `docker compose up --build`
  - Tests hit the real HTTP endpoints (no mocks)

Install test deps:
  pip install pytest httpx pytest-asyncio
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import httpx
import pytest
from helpers import BASE_URLS, auth_headers, register_and_login


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def farmer_token():
    return register_and_login(
        email="farmer_test@soko.io",
        password="farmerpass123",
        full_name="Test Farmer",
        role="farmer",
    )


@pytest.fixture(scope="session")
def buyer_token():
    return register_and_login(
        email="buyer_test@soko.io",
        password="buyerpass123",
        full_name="Test Buyer",
        role="buyer",
    )


@pytest.fixture(scope="session")
def farmer_profile(farmer_token):
    resp = httpx.post(
        f"{BASE_URLS['farmer']}/farmers/profile",
        json={"full_name": "Test Farmer", "phone": "+256700000001", "district": "Kampala"},
        headers=auth_headers(farmer_token),
    )
    if resp.status_code in (200, 201):
        return resp.json()
    # Profile already exists — fetch it
    assert resp.status_code == 400, f"Farmer profile setup failed unexpectedly: {resp.text}"
    get = httpx.get(f"{BASE_URLS['farmer']}/farmers/profile", headers=auth_headers(farmer_token))
    assert get.status_code == 200, f"Could not fetch existing farmer profile: {get.text}"
    return get.json()


@pytest.fixture(scope="session")
def buyer_profile(buyer_token):
    resp = httpx.post(
        f"{BASE_URLS['buyer']}/buyers/profile",
        json={"full_name": "Test Buyer", "phone": "+256700000002", "district": "Kampala"},
        headers=auth_headers(buyer_token),
    )
    if resp.status_code in (200, 201):
        return resp.json()
    # Profile already exists — fetch it
    assert resp.status_code == 400, f"Buyer profile setup failed unexpectedly: {resp.text}"
    get = httpx.get(f"{BASE_URLS['buyer']}/buyers/profile", headers=auth_headers(buyer_token))
    assert get.status_code == 200, f"Could not fetch existing buyer profile: {get.text}"
    return get.json()


@pytest.fixture(scope="session")
def produce_listing(farmer_token, farmer_profile):
    resp = httpx.post(
        f"{BASE_URLS['produce']}/produce/",
        json={
            "name": "Test Tomatoes",
            "description": "Fresh tomatoes for testing",
            "category": "vegetables",
            "unit": "kg",
            "quantity": 100.0,
            "price_per_unit": 2500.0,
            "district": "Kampala",
        },
        headers=auth_headers(farmer_token),
    )
    assert resp.status_code == 201, f"Produce listing setup failed: {resp.text}"
    return resp.json()


@pytest.fixture(scope="session")
def placed_order(buyer_token, buyer_profile, produce_listing):
    resp = httpx.post(
        f"{BASE_URLS['buyer']}/orders/",
        json={
            "produce_id": produce_listing["id"],
            "quantity_kg": 5.0,
        },
        headers=auth_headers(buyer_token),
    )
    assert resp.status_code == 201, f"Order placement failed: {resp.text}"
    return resp.json()
