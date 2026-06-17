"""User registration, login, and profile management.

Uses stdlib PBKDF2-HMAC-SHA256 for password hashing (no bcrypt dependency).
Integrates with existing JWT token system in core_engines/auth.
"""

import hashlib
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core_engines.auth.auth import (
    create_session_token,
    create_refresh_token,
    verify_token,
)
from database.db import SessionLocal
from database.models import User

router = APIRouter(prefix="/api/auth/users", tags=["auth-users"])


# ─── Password helpers (PBKDF2-HMAC-SHA256, stdlib only) ───────────────

def _hash_password(password: str) -> str:
    salt = os.urandom(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return salt.hex() + ":" + dk.hex()


def _verify_password(password: str, stored: str) -> bool:
    salt_hex, dk_hex = stored.split(":")
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return dk.hex() == dk_hex


# ─── Schemas ─────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str


# ─── Endpoints ───────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest):
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if len(body.username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")

    session = SessionLocal()
    try:
        if session.query(User).filter(
            (User.username == body.username) | (User.email == body.email)
        ).first():
            raise HTTPException(409, "Username or email already exists")

        user = User(
            username=body.username,
            email=body.email,
            password_hash=_hash_password(body.password),
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        access_token = create_session_token(
            user_id=str(user.id),
            meta={"username": user.username, "email": user.email},
        )
        refresh_token = create_refresh_token(user_id=str(user.id))
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    finally:
        session.close()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == body.username).first()
        if not user or not _verify_password(body.password, user.password_hash):
            raise HTTPException(401, "Invalid username or password")
        if not user.is_active:
            raise HTTPException(403, "Account is disabled")

        access_token = create_session_token(
            user_id=str(user.id),
            meta={"username": user.username, "email": user.email},
        )
        refresh_token = create_refresh_token(user_id=str(user.id))
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    finally:
        session.close()


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest):
    data = verify_token(body.refresh_token)
    if data is None or data.get("type") != "refresh":
        raise HTTPException(401, "Invalid or expired refresh token")

    user_id = data.get("sub")
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(401, "User not found or inactive")

        new_access = create_session_token(
            user_id=str(user.id),
            meta={"username": user.username, "email": user.email},
        )
        new_refresh = create_refresh_token(user_id=str(user.id))
        return TokenResponse(access_token=new_access, refresh_token=new_refresh)
    finally:
        session.close()


@router.get("/me", response_model=UserProfile)
def get_profile(request: Request):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "Not authenticated")
    data = verify_token(token)
    if data is None:
        raise HTTPException(401, "Invalid or expired token")
    user_id = data.get("sub")

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(404, "User not found")
        return UserProfile(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
        )
    finally:
        session.close()
