"""Tests for auth middleware and rate limiting."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from api.main import app
    from core_engines.license.validator import generate_license
    c = TestClient(app)
    # Activate license
    lic = generate_license(expiry_days=365)
    c.post("/api/license/activate", json={"key": lic})
    return c


@pytest.fixture(autouse=True)
def reset_limiter():
    from core_engines.gateway.rate_limit import reset_rate_limiter
    reset_rate_limiter()


def _login(c, device_id: str = "test-device") -> str:
    resp = c.post("/api/auth/login", json={"device_id": device_id})
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


class TestAuthMiddleware:
    def test_public_health_no_auth(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_public_auth_login_no_auth(self, client):
        resp = client.post("/api/auth/login", json={"device_id": "test"})
        assert resp.status_code == 200

    def test_protected_no_token_returns_401(self, client):
        resp = client.get("/api/targets")
        assert resp.status_code == 401

    def test_protected_invalid_token_returns_401(self, client):
        resp = client.get("/api/targets", headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401

    def test_protected_valid_token_succeeds(self, client):
        token = _login(client)
        resp = client.get("/api/targets", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_protected_expired_token_returns_401(self, client):
        resp = client.get("/api/targets", headers={"Authorization": "Bearer eyJleHAiOjB9.signature"})
        assert resp.status_code == 401

    def test_all_routers_require_auth(self, client):
        protected = [
            "/api/targets",
            "/api/endpoints",
            "/api/findings",
            "/api/evidence",
            "/api/opportunities",
            "/api/overview",
            "/api/system/health",
            "/api/execution/tracker",
            "/api/stats",
        ]
        for path in protected:
            resp = client.get(path)
            assert resp.status_code == 401, f"{path} should require auth, got {resp.status_code}"

    def test_missing_auth_header_format(self, client):
        resp = client.get("/api/targets", headers={"Authorization": "NotBearer something"})
        assert resp.status_code == 401


class TestRateLimit:
    def test_login_rate_limit(self, client):
        for _ in range(15):
            client.post("/api/auth/login", json={"device_id": "rate-test"})
        resp = client.post("/api/auth/login", json={"device_id": "rate-test"})
        assert resp.status_code == 429

    def test_rate_limit_headers(self, client):
        resp = client.get("/api/health")
        # Health is not rate-limited, so no X-RateLimit header expected
        assert "X-RateLimit-Remaining" not in resp.headers

    def test_normal_request_has_remaining_header(self, client):
        token = _login(client)
        resp = client.get("/api/system/health", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        # Rate limited endpoints should have the header
        assert "X-RateLimit-Remaining" in resp.headers
