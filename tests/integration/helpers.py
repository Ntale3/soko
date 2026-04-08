import httpx

BASE_URLS = {
    "auth":           "http://localhost:8001",
    "farmer":         "http://localhost:8002",
    "buyer":          "http://localhost:8003",
    "produce":        "http://localhost:8004",
    "recommendation": "http://localhost:8005",
}


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_and_login(email: str, password: str, full_name: str, role: str) -> str:
    """Register a user (ignores 409 if already exists) and return a JWT access token."""
    import hashlib
    phone_suffix = int(hashlib.md5(email.encode()).hexdigest()[:7], 16) % 9000000 + 1000000
    httpx.post(f"{BASE_URLS['auth']}/auth/register", json={
        "email": email,
        "fullName": full_name,
        "password": password,
        "phone": f"+25670{phone_suffix}",
        "district": "Kampala",
        "role": role,
    })
    resp = httpx.post(f"{BASE_URLS['auth']}/auth/login", json={
        "email": email,
        "password": password,
    })
    resp.raise_for_status()
    return resp.json()["tokens"]["access_token"]
