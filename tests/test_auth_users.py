"""Tests for user registration, login, and profile endpoints."""

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
    return c


@pytest.fixture(autouse=True)
def clean_users():
    """Remove test users after each test."""
    yield
    from database.db import SessionLocal
    from database.models import User

    session = SessionLocal()
    try:
        session.query(User).filter(
            User.username.like("testuser%")
        ).delete()
        session.commit()
    finally:
        session.close()


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/auth/users/register", json={
            "username": "testuser1",
            "email": "test1@example.com",
            "password": "strongpass123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_username(self, client):
        client.post("/api/auth/users/register", json={
            "username": "testuser2",
            "email": "test2@example.com",
            "password": "strongpass123",
        })
        resp = client.post("/api/auth/users/register", json={
            "username": "testuser2",
            "email": "other@example.com",
            "password": "strongpass123",
        })
        assert resp.status_code == 409

    def test_register_short_password(self, client):
        resp = client.post("/api/auth/users/register", json={
            "username": "testuser3",
            "email": "test3@example.com",
            "password": "short",
        })
        assert resp.status_code == 400

    def test_register_short_username(self, client):
        resp = client.post("/api/auth/users/register", json={
            "username": "ab",
            "email": "test4@example.com",
            "password": "strongpass123",
        })
        assert resp.status_code == 400


class TestLogin:
    def test_login_success(self, client):
        client.post("/api/auth/users/register", json={
            "username": "testuser5",
            "email": "test5@example.com",
            "password": "strongpass123",
        })
        resp = client.post("/api/auth/users/login", json={
            "username": "testuser5",
            "password": "strongpass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_wrong_password(self, client):
        client.post("/api/auth/users/register", json={
            "username": "testuser6",
            "email": "test6@example.com",
            "password": "strongpass123",
        })
        resp = client.post("/api/auth/users/login", json={
            "username": "testuser6",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_login_nonexistent(self, client):
        resp = client.post("/api/auth/users/login", json={
            "username": "nobody",
            "password": "strongpass123",
        })
        assert resp.status_code == 401


class TestProfile:
    def test_me_authenticated(self, client):
        reg = client.post("/api/auth/users/register", json={
            "username": "testuser7",
            "email": "test7@example.com",
            "password": "strongpass123",
        })
        token = reg.json()["access_token"]

        resp = client.get("/api/auth/users/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        profile = resp.json()
        assert profile["username"] == "testuser7"
        assert profile["email"] == "test7@example.com"
        assert "id" in profile
        assert "created_at" in profile

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/auth/users/me")
        assert resp.status_code == 401


class TestRefresh:
    def test_refresh_token(self, client):
        reg = client.post("/api/auth/users/register", json={
            "username": "testuser8",
            "email": "test8@example.com",
            "password": "strongpass123",
        })
        refresh_token = reg.json()["refresh_token"]

        resp = client.post("/api/auth/users/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_invalid_token(self, client):
        resp = client.post("/api/auth/users/refresh", json={
            "refresh_token": "invalid-token",
        })
        assert resp.status_code == 401
