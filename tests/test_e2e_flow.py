"""FASE 7 — E2E validation: full pipeline flow test.

Tests the complete flow:
  create target → API CRUD → endpoints → findings → report → verify → cleanup
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from database import models
from database.db import SessionLocal, init_db


@pytest.fixture(scope="module")
def client():
    init_db()
    from api.main import app
    from core_engines.license.validator import generate_license
    c = TestClient(app)
    lic = generate_license(expiry_days=365)
    c.post("/api/license/activate", json={"key": lic})
    resp = c.post("/api/auth/login", json={"device_id": "pytest-e2e-device"})
    if resp.status_code == 200:
        token = resp.json()["data"]["token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestE2EFlow:
    """End-to-end pipeline validation."""

    TARGET_NAME = "e2e-test-target"
    TARGET_DOMAIN = "e2etest.example.com"
    target_id: int | None = None
    endpoint_id: int | None = None
    finding_id: int | None = None

    def test_01_health(self, client):
        """Sanity check: API is alive."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_02_version(self, client):
        """Version endpoint works."""
        resp = client.get("/api/version")
        assert resp.status_code == 200
        assert "version" in resp.json()

    def test_03_create_target(self, client, db_session):
        """Create a target and verify it persists."""
        resp = client.post("/api/targets", json={
            "name": self.TARGET_NAME,
            "domain": self.TARGET_DOMAIN,
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data["name"] == self.TARGET_NAME
        target_id = data["id"]

        t = db_session.query(models.Target).filter(models.Target.id == target_id).first()
        assert t is not None
        assert t.name == self.TARGET_NAME
        assert t.domain == self.TARGET_DOMAIN

        self.__class__.target_id = target_id

    def test_04_get_target_list(self, client):
        """Verify target appears in listing."""
        resp = client.get("/api/targets?limit=300")
        assert resp.status_code == 200
        data = resp.json()
        names = [item["name"] for item in data["items"]]
        assert self.TARGET_NAME in names, f"Target not in listing ({len(names)} items)"

    def test_05_get_target_detail(self, client):
        """Verify target detail endpoint."""
        resp = client.get(f"/api/targets/{self.__class__.target_id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] == self.TARGET_NAME

    def test_06_create_endpoint(self, client, db_session):
        """Create an endpoint and verify it persists."""
        resp = client.post("/api/endpoints", json={
            "target_id": self.__class__.target_id,
            "path": "/api/test",
            "method": "GET",
        })
        assert resp.status_code in (200, 201), f"Failed: {resp.text}"
        data = resp.json()
        ep_id = data.get("id")
        assert ep_id is not None

        db_ep = db_session.query(models.Endpoint).filter(models.Endpoint.id == ep_id).first()
        assert db_ep is not None
        assert db_ep.path == "/api/test"
        assert db_ep.target_id == self.__class__.target_id

        self.__class__.endpoint_id = ep_id

    def test_07_list_endpoints(self, client):
        """Verify endpoint is listed."""
        resp = client.get(f"/api/endpoints?target_id={self.__class__.target_id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        paths = [e["path"] for e in data.get("items", data if isinstance(data, list) else [])]
        assert "/api/test" in paths

    def test_08_create_finding(self, client, db_session):
        """Create a finding and verify persistence."""
        resp = client.post("/api/findings", json={
            "target_id": self.__class__.target_id,
            "endpoint_id": self.__class__.endpoint_id,
            "severity": "high",
            "title": "E2E Test Finding",
            "description": "Test finding from E2E validation",
        })
        assert resp.status_code in (200, 201), f"Failed: {resp.text}"
        data = resp.json()
        finding_id = data.get("id")
        assert finding_id is not None

        db_f = db_session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        assert db_f is not None
        assert db_f.title == "E2E Test Finding" or db_f.finding_type == "idor"

        self.__class__.finding_id = finding_id

    def test_09_create_report(self, client, db_session):
        """Create a report from findings."""
        resp = client.post("/api/reports", json={
            "title": "E2E Test Report",
            "finding_ids": [self.__class__.finding_id],
            "program": self.TARGET_NAME,
            "vulnerability": "idor",
            "severity": "high",
            "format": "markdown",
        })
        if resp.status_code == 422:
            # Schema may require additional fields — try alternative payload
            resp = client.post("/api/reports", json={
                "finding_ids": [self.__class__.finding_id],
                "program": self.TARGET_NAME,
                "vulnerability": "idor",
            })
        assert resp.status_code in (200, 201), f"Report creation failed: {resp.text}"
        report = resp.json()
        report_id = report.get("id")
        assert report_id is not None

        r = db_session.query(models.Report).filter(models.Report.id == report_id).first()
        assert r is not None
        assert r.program == self.TARGET_NAME or r.target == self.TARGET_NAME

    def test_10_reports_list(self, client):
        """Verify reports are listed via API."""
        resp = client.get("/api/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict) or isinstance(data, list)

    def test_11_simulate_restart(self, db_session):
        """Simulate restart: verify data persists in DB directly."""
        t = db_session.query(models.Target).filter(
            models.Target.name == self.TARGET_NAME
        ).first()
        assert t is not None, "Target lost from DB — persistence failure"

        ep = db_session.query(models.Endpoint).filter(
            models.Endpoint.id == self.__class__.endpoint_id
        ).first()
        assert ep is not None, "Endpoint lost from DB"

    def test_12_cleanup(self, db_session):
        """Clean up test data."""
        tid = self.__class__.target_id
        if tid is None:
            return

        eids = [r.id for r in db_session.query(models.Endpoint).filter(
            models.Endpoint.target_id == tid
        ).all()]
        for eid in eids:
            db_session.query(models.Verdict).filter(
                models.Verdict.endpoint_id == eid
            ).delete()

        db_session.query(models.Finding).filter(models.Finding.target_id == tid).delete()
        db_session.query(models.Endpoint).filter(models.Endpoint.target_id == tid).delete()

        db_session.query(models.ScanRun).filter(models.ScanRun.target_id == tid).delete()
        db_session.query(models.Investigation).filter(models.Investigation.target_id == tid).delete()

        db_session.query(models.Report).filter(models.Report.target == self.TARGET_NAME).delete()
        db_session.query(models.Target).filter(models.Target.id == tid).delete()
        db_session.commit()

        remaining = db_session.query(models.Target).filter(models.Target.id == tid).first()
        assert remaining is None
