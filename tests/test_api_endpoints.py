"""Integration tests for critical API endpoints."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from api.main import app
    from core_engines.license.validator import generate_license
    c = TestClient(app)
    # Activate a license first
    lic = generate_license(expiry_days=365)
    c.post("/api/license/activate", json={"key": lic})
    # Authenticate once for the whole module
    resp = c.post("/api/auth/login", json={"device_id": "pytest-device"})
    if resp.status_code == 200:
        token = resp.json()["data"]["token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
    return c


class TestHealth:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_version(self, client):
        resp = client.get("/api/version")
        assert resp.status_code == 200
        assert "version" in resp.json()


class TestTargets:
    def test_list_targets(self, client):
        resp = client.get("/api/targets")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 0

    def test_target_detail(self, client):
        resp = client.get("/api/targets/1")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "name" in data


class TestEndpoints:
    def test_list_endpoints(self, client):
        resp = client.get("/api/endpoints")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 0

    def test_filter_by_target(self, client):
        resp = client.get("/api/endpoints?target_id=1")
        assert resp.status_code == 200


class TestFindings:
    def test_list_findings(self, client):
        resp = client.get("/api/findings")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data


class TestOverview:
    def test_overview(self, client):
        resp = client.get("/api/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "target_count" in data
        assert "endpoint_count" in data
        assert isinstance(data["target_count"], int)
        assert isinstance(data["endpoint_count"], int)

    def test_system_health(self, client):
        resp = client.get("/api/system/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "database" in data


class TestExecution:
    def test_tracker(self, client):
        resp = client.get("/api/execution/tracker")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_executions" in data

    def test_actions(self, client):
        resp = client.get("/api/execution/actions")
        assert resp.status_code == 200
        data = resp.json()
        assert "actions" in data
        assert "count" in data

    def test_decisions(self, client):
        resp = client.get("/api/execution/decisions")
        assert resp.status_code == 200
        data = resp.json()
        assert "decisions" in data
        assert "count" in data

    def test_insights(self, client):
        resp = client.get("/api/execution/insights")
        assert resp.status_code == 200
        data = resp.json()
        assert "insights" in data
        assert "count" in data

    def test_explanations(self, client):
        resp = client.get("/api/execution/explain")
        assert resp.status_code == 200
        data = resp.json()
        assert "explanations" in data

    def test_traces(self, client):
        resp = client.get("/api/execution/traces")
        assert resp.status_code == 200
        data = resp.json()
        assert "traces" in data

    def test_scorecard(self, client):
        resp = client.get("/api/execution/scorecard")
        assert resp.status_code == 200

    def test_outcomes(self, client):
        resp = client.get("/api/execution/outcomes")
        assert resp.status_code == 200


class TestDaily:
    def test_briefing(self, client):
        resp = client.get("/api/daily/briefing")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        briefing = data["data"]["briefing"]
        assert isinstance(briefing, dict)
        assert len(briefing) > 0

    def test_minimal(self, client):
        resp = client.get("/api/daily/minimal")
        assert resp.status_code == 200


class TestOpportunities:
    def test_list(self, client):
        resp = client.get("/api/opportunities")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_opportunity_overview(self, client):
        resp = client.get("/api/opportunity/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data or "opportunities_total" in data


class TestCreateTarget:
    def test_create_target(self, client):
        resp = client.post("/api/targets", json={"name": "test-target", "domain": "test.example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["name"] == "test-target"

    def test_create_and_fetch(self, client):
        create = client.post("/api/targets", json={"name": "create-fetch-test"})
        assert create.status_code == 200
        tid = create.json()["id"]
        fetch = client.get(f"/api/targets/{tid}")
        assert fetch.status_code == 200
        assert fetch.json()["name"] == "create-fetch-test"

    def test_create_endpoint(self, client):
        resp = client.post("/api/endpoints", json={"target_id": 1, "path": "/api/test", "method": "GET"})
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["path"] == "/api/test"

    def test_create_finding(self, client):
        resp = client.post("/api/findings", json={
            "target_id": 1, "endpoint_id": 1,
            "title": "test finding", "severity": "medium",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["title"] == "test finding"


class TestStats:
    def test_stats(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200


class TestContracts:
    def test_opportunity_recommendations(self, client):
        resp = client.get("/api/opportunity/recommendations")
        assert resp.status_code == 200

    def test_operations_morning_brief(self, client):
        resp = client.get("/api/operations/briefing/morning")
        assert resp.status_code == 200
        data = resp.json()
        assert "generated_at" in data


class TestWebSocket:
    def test_websocket_endpoint_registered(self, client):
        """WebSocket /api/ws is registered and accepts connection with valid token."""
        token = client.headers["Authorization"].removeprefix("Bearer ")
        with client.websocket_connect(f"/api/ws?token={token}") as ws:
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_websocket_rejects_no_token(self):
        """WebSocket without token should close with code 4001."""
        from fastapi.testclient import TestClient
        from api.main import app
        from starlette.websockets import WebSocketDisconnect

        c = TestClient(app)
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with c.websocket_connect("/api/ws") as ws:
                ws.receive_text()
        assert excinfo.value.code == 4001
