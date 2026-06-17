"""Tests for the Personal Learning Engine (PLE)."""

from __future__ import annotations

import pytest


# ─── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from api.main import app
    from core_engines.license.validator import generate_license

    c = TestClient(app)
    lic = generate_license(expiry_days=365)
    c.post("/api/license/activate", json={"key": lic})

    # Ensure clean user for testing
    from database.db import SessionLocal
    from database.models import User
    s = SessionLocal()
    s.query(User).filter(User.username == "ple_test_user").delete()
    s.commit()
    s.close()

    # Register a test user and get token
    reg = c.post("/api/auth/users/register", json={
        "username": "ple_test_user",
        "email": "ple@test.com",
        "password": "ple_test_pass_123",
    })
    token = reg.json()["access_token"]
    c.headers = {"Authorization": f"Bearer {token}"}
    return c


@pytest.fixture(autouse=True)
def clean_ple_data(request):
    """Clean up PLE data after each test."""
    yield
    from core_engines.learning import get_profile_service
    # Get the actual user_id from the module-scoped client fixture
    client = request.getfixturevalue("client")
    from core_engines.auth.auth import verify_token
    tok = client.headers.get("Authorization", "").removeprefix("Bearer ")
    data = verify_token(tok)
    if data:
        uid = data.get("sub", "")
        svc = get_profile_service()
        svc.reset(uid)
        # Also clean up learning events
        from database.db import SessionLocal
        from core_engines.learning.profile import LearningEvent
        s = SessionLocal()
        s.query(LearningEvent).filter(LearningEvent.user_id == uid).delete()
        s.commit()
        s.close()


# ─── Profile Tests ────────────────────────────────────────────────────────

class TestProfile:
    def test_get_profile_empty(self, client):
        resp = client.get("/api/learning/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["exists"] is True or data["exists"] is False

    def test_reset_profile(self, client):
        resp = client.post("/api/learning/profile/reset")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_update_preferences(self, client):
        resp = client.patch("/api/learning/preferences", json={"adaptive_mode": False})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify
        prof = client.get("/api/learning/profile")
        assert prof.json()["adaptive_mode"] is False


# ─── Event Tracking Tests ─────────────────────────────────────────────────

class TestEventTracking:
    def test_track_target_viewed(self, client):
        resp = client.post("/api/learning/events", json={
            "event_type": "target_viewed",
            "data": {"industry": "finance", "technology": "aws", "domain": "example.com"},
        })
        assert resp.status_code == 200

        prof = client.get("/api/learning/profile")
        assert prof.json()["discovery"]["total_targets"] >= 1
        assert "finance" in prof.json()["discovery"]["industries"]
        assert "aws" in prof.json()["discovery"]["technologies"]

    def test_track_finding_created(self, client):
        resp = client.post("/api/learning/events", json={
            "event_type": "finding_created",
            "data": {"bug_class": "IDOR", "severity": "high"},
        })
        assert resp.status_code == 200

        prof = client.get("/api/learning/profile")
        assert prof.json()["success_history"]["high_severity_findings"] >= 1

    def test_track_module_visited(self, client):
        resp = client.post("/api/learning/events", json={
            "event_type": "module_visited",
            "data": {"module": "targets"},
        })
        assert resp.status_code == 200

        prof = client.get("/api/learning/profile")
        modules = prof.json()["activity"]["favorite_modules"]
        assert any(m.get("module") == "targets" for m in modules)

    def test_track_session(self, client):
        client.post("/api/learning/events", json={"event_type": "session_started", "data": {}})
        resp = client.post("/api/learning/events", json={
            "event_type": "session_ended",
            "data": {"duration_minutes": 120},
        })
        assert resp.status_code == 200

        prof = client.get("/api/learning/profile")
        assert prof.json()["activity"]["total_sessions"] >= 1
        assert prof.json()["activity"]["total_hours_active"] >= 2.0

    def test_list_events(self, client):
        client.post("/api/learning/events", json={"event_type": "test_event", "data": {"key": "val"}})
        resp = client.get("/api/learning/events")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 1
        assert any(e["event_type"] == "test_event" for e in events)


# ─── Prioritization Tests ─────────────────────────────────────────────────

class TestPrioritization:
    def test_prioritize_targets_no_profile(self, client):
        # Reset first (no profile data means neutral scoring)
        client.post("/api/learning/profile/reset")
        resp = client.post("/api/learning/prioritize/targets", json={
            "targets": [
                {"name": "target1", "industry": "finance"},
                {"name": "target2", "industry": "healthcare"},
            ],
        })
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 2

    def test_prioritize_targets_with_profile(self, client):
        # Create profile with finance preference
        client.post("/api/learning/events", json={
            "event_type": "target_viewed",
            "data": {"industry": "finance", "technology": "aws", "domain": "bank.com"},
        })

        resp = client.post("/api/learning/prioritize/targets", json={
            "targets": [
                {"name": "bank", "industry": "finance", "technology": "aws"},
                {"name": "hospital", "industry": "healthcare", "technology": "azure"},
            ],
        })
        assert resp.status_code == 200
        results = resp.json()
        # Finance target should have higher score due to preference match
        bank_item = next(r for r in results if r["item"]["name"] == "bank")
        assert bank_item["score"] > 0
        assert any("finance" in e for e in bank_item["explanations"])

    def test_prioritize_findings(self, client):
        # Build IDOR preference
        client.post("/api/learning/events", json={
            "event_type": "finding_created",
            "data": {"bug_class": "IDOR", "severity": "medium"},
        })
        client.post("/api/learning/events", json={
            "event_type": "finding_created",
            "data": {"bug_class": "IDOR", "severity": "medium"},
        })

        resp = client.post("/api/learning/prioritize/findings", json={
            "findings": [
                {"bug_class": "IDOR", "severity": "high"},
                {"bug_class": "XXE", "severity": "high"},
            ],
        })
        assert resp.status_code == 200
        results = resp.json()
        idor_item = next(r for r in results if r["item"]["bug_class"] == "IDOR")
        assert idor_item["score"] > 0

    def test_prioritization_disabled_in_adaptive_off(self, client):
        client.patch("/api/learning/preferences", json={"adaptive_mode": False})
        resp = client.post("/api/learning/prioritize/targets", json={
            "targets": [{"name": "t1", "industry": "finance"}],
        })
        assert resp.status_code == 200
        results = resp.json()
        assert results[0]["score"] == 0.0  # No adaptive scoring


# ─── Explanation Tests ────────────────────────────────────────────────────

class TestExplanations:
    def test_explain_priority(self, client):
        client.post("/api/learning/events", json={
            "event_type": "target_viewed",
            "data": {"industry": "finance"},
        })
        resp = client.post("/api/learning/explain/priority", json={
            "targets": [{"name": "bank", "industry": "finance"}],
        })
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert any("finance" in e for e in results[0]["explanations"])

    def test_profile_summary(self, client):
        resp = client.get("/api/learning/explain/profile-summary")
        assert resp.status_code == 200
        assert "summary" in resp.json()


# ─── AI Memory Tests ──────────────────────────────────────────────────────

class TestMemory:
    def test_context(self, client):
        client.post("/api/learning/events", json={
            "event_type": "target_viewed",
            "data": {"industry": "finance", "technology": "aws"},
        })
        resp = client.post("/api/learning/memory/context", json={
            "target": {"industry": "finance", "technology": "aws"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "context" in data
        assert "finance" in data["context"]

    def test_similar_findings(self, client):
        client.post("/api/learning/events", json={
            "event_type": "finding_created",
            "data": {"bug_class": "SQLi", "severity": "high"},
        })
        resp = client.get("/api/learning/memory/similar-findings", params={"bug_class": "SQLi"})
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1


# ─── Daily Recommendations Tests ──────────────────────────────────────────

class TestRecommendations:
    def test_daily_recommendations(self, client):
        client.post("/api/learning/events", json={
            "event_type": "finding_created",
            "data": {"bug_class": "IDOR", "severity": "high"},
        })
        resp = client.get("/api/learning/recommendations/daily")
        assert resp.status_code == 200
        recs = resp.json()
        assert isinstance(recs, list)


# ─── Export Tests ─────────────────────────────────────────────────────────

class TestExport:
    def test_export_json(self, client):
        resp = client.get("/api/learning/export", params={"fmt": "json"})
        assert resp.status_code == 200
        import json
        data = json.loads(resp.text)
        assert "exists" in data

    def test_export_markdown(self, client):
        resp = client.get("/api/learning/export", params={"fmt": "markdown"})
        assert resp.status_code == 200
        assert resp.text.startswith("# Investigator Profile")
