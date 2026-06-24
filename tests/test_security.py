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

    # ── Desktop auth hardening: frontend assets must never require auth ──

    def test_frontend_root_does_not_require_auth(self, client):
        """The SPA entry point (/) must load without auth."""
        resp = client.get("/")
        assert resp.status_code != 401, "SPA root must not return 401"

    def test_frontend_assets_do_not_require_auth(self, client):
        """Static assets like /assets/* must load without auth."""
        resp = client.get("/assets/some-file.js")
        assert resp.status_code != 401, "Static assets must not return 401"

    def test_spa_routes_do_not_require_auth(self, client):
        """SPA routes like /daily, /settings must not 401."""
        for route in ("/daily", "/settings", "/intelligence", "/radar"):
            resp = client.get(route)
            assert resp.status_code != 401, f"SPA route {route} must not return 401"

    def test_favicon_does_not_require_auth(self, client):
        resp = client.get("/favicon.ico")
        assert resp.status_code != 401

    # ── Desktop session auto-creation ──

    def test_desktop_session_creation(self):
        """The _create_desktop_session function must produce a valid token."""
        from desktop.settings import get_settings, DesktopSettings
        from desktop.main_desktop import _create_desktop_session
        from api.main import app
        from fastapi.testclient import TestClient

        settings = get_settings()
        # Save the token if any (singleton may have one from other tests)
        old_token = settings.get("session_token")
        settings.set("session_token", None)
        _create_desktop_session(8000)
        token = settings.get("session_token")
        assert token is not None, "desktop session must create a token"
        # Restore old token
        if old_token:
            settings.set("session_token", old_token)

        # The token must work against private API
        c = TestClient(app)
        resp = c.get("/api/targets", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, f"desktop token must authenticate, got {resp.status_code}"

    def test_desktop_session_not_expired(self):
        """Freshly created session must not be expired."""
        from desktop.settings import get_settings
        from desktop.main_desktop import _create_desktop_session
        from api.main import app
        from fastapi.testclient import TestClient

        settings = get_settings()
        old_token = settings.get("session_token")
        settings.set("session_token", None)
        _create_desktop_session(8000)
        token = settings.get("session_token")
        if old_token:
            settings.set("session_token", old_token)
        c = TestClient(app)
        resp = c.get("/api/targets", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_invalid_paths_still_404_not_401(self, client):
        """Unknown non-API paths should 404, not 401."""
        for path in ("/nonexistent", "/images/missing.png"):
            resp = client.get(path)
            assert resp.status_code != 401, f"{path} must not return 401 (got {resp.status_code})"

    def test_all_api_routes_still_require_auth(self, client):
        """Every /api/* endpoint (except public) must require auth."""
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
            "/api/daily/briefing",
            "/api/operations/tasks",
            "/api/assistant/insights",
        ]
        for path in protected:
            resp = client.get(path)
            assert resp.status_code == 401, f"{path} should require auth, got {resp.status_code}"

    def test_static_file_paths_under_api_still_protected(self, client):
        """Even non-existent /api sub-paths must require auth (no info leak)."""
        resp = client.get("/api/secrets")
        assert resp.status_code != 200, "/api/secrets must not be accessible without auth"


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
