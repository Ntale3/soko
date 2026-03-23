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
    httpx.post(f"{BASE_URLS['auth']}/auth/register", json={
        "email": email,
        "full_name": full_name,
        "password": password,
        "role": role,
    })
    resp = httpx.post(f"{BASE_URLS['auth']}/auth/login", data={
        "username": email,
        "password": password,
    })
    resp.raise_for_status()
    return resp.json()["access_token"]
