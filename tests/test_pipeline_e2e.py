"""End-to-end smoke test for the core pipeline.

Tests the flow: Target → Endpoints → Hypothesis → Investigation → Dashboard → Report.

Validation requires identity/session setup and is tested separately.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from api.main import app
    from core_engines.license.validator import generate_license
    c = TestClient(app)
    lic = generate_license(expiry_days=365)
    c.post("/api/license/activate", json={"key": lic})
    resp = c.post("/api/auth/login", json={"device_id": "pytest-e2e"})
    if resp.status_code == 200:
        token = resp.json()["data"]["token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
    return c


class TestPipelineE2E:
    """Verifies the core pipeline end-to-end."""

    TARGET_NAME = "e2e-smoke-target"
    TARGET_DOMAIN = "smoke.example.com"

    def test_01_create_target(self, client):
        resp = client.post("/api/targets", json={
            "name": self.TARGET_NAME,
            "domain": self.TARGET_DOMAIN,
        })
        assert resp.status_code == 200, f"Create target failed: {resp.text}"
        data = resp.json()
        assert data["name"] == self.TARGET_NAME
        assert data["id"] > 0
        pytest._target_id = data["id"]

    def test_02_create_endpoints(self, client):
        target_id = pytest._target_id
        endpoints = [
            {"target_id": target_id, "path": "/api/users", "method": "GET"},
            {"target_id": target_id, "path": "/api/users/1", "method": "GET"},
            {"target_id": target_id, "path": "/api/admin", "method": "GET"},
            {"target_id": target_id, "path": "/graphql", "method": "POST"},
            {"target_id": target_id, "path": "/api/login", "method": "POST"},
        ]
        ids = []
        for ep in endpoints:
            resp = client.post("/api/endpoints", json=ep)
            assert resp.status_code == 200, f"Create endpoint failed: {resp.text}"
            ids.append(resp.json()["id"])
        assert len(ids) == 5
        pytest._endpoint_ids = ids

    def test_03_run_hypotheses(self, client):
        target_id = pytest._target_id
        resp = client.post(f"/api/hypotheses/{target_id}")
        assert resp.status_code == 200, f"Hypotheses failed: {resp.text}"
        data = resp.json()
        assert data["total_hypotheses"] > 0
        assert len(data["attack_queue"]) > 0
        assert data["top_priority"] is not None
        assert data["summary"] is not None
        pytest._hypothesis_output = data

    def test_04_create_investigation(self, client):
        target_id = pytest._target_id
        top = pytest._hypothesis_output["top_priority"]
        inv_name = f"{top['vulnerability_type']} — {self.TARGET_NAME}"
        resp = client.post("/api/investigations", json={
            "target_id": target_id,
            "name": inv_name,
            "notes": f"Promoted from hypothesis: {top['reasoning'][:200]}",
            "tags": [top["vulnerability_type"], "from_hypothesis"],
        })
        assert resp.status_code == 200, f"Create investigation failed: {resp.text}"
        data = resp.json()
        assert data["name"] == inv_name
        assert data["status"] == "active"
        assert data["target_id"] == target_id
        pytest._investigation_id = data["id"]

    def test_05_investigation_dashboard(self, client):
        inv_id = pytest._investigation_id
        resp = client.get(f"/api/investigations/{inv_id}/dashboard")
        assert resp.status_code == 200, f"Dashboard failed: {resp.text}"
        data = resp.json()
        assert "investigation" in data
        assert "stats" in data
        assert "pipeline" in data
        pipeline = data["pipeline"]
        assert "stages" in pipeline
        assert "timeline" in pipeline
        assert "overall_confidence" in pipeline
        assert "progress_pct" in pipeline

    def test_06_generate_report(self, client):
        resp = client.get("/api/reports/generate")
        assert resp.status_code == 200, f"Generate report failed: {resp.text}"
        data = resp.json()
        assert "title" in data
        assert "findings" in data
        assert "markdown" in data
        assert data["total_findings"] >= 0

    def test_07_cleanup(self, client):
        inv_id = pytest._investigation_id
        resp = client.delete(f"/api/investigations/{inv_id}")
        assert resp.status_code == 200, f"Delete investigation failed: {resp.status_code}"
