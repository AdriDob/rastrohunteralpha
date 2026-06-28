from __future__ import annotations

import logging
from datetime import datetime, timezone

from core_engines.target_auth.identity_manager import get_identity_manager
from core_engines.target_auth.login_service import TargetLoginService
from core_engines.target_auth.vault import get_credential_vault
from database import db, models

logger = logging.getLogger("rastro.target_auth.session")


class TargetSessionManager:
    """Manages active sessions for target identities.

    Handles login, token refresh, expiry detection, and
    provides AuthContext-compatible output for the replayer.
    """

    def __init__(self) -> None:
        self._login_service = TargetLoginService()
        self._identity_manager = get_identity_manager()
        self._vault = get_credential_vault()

    # ── Public API ─────────────────────────────────────────────────

    def ensure_session(self, identity_id: int) -> dict:
        """Ensure a valid session exists for the given identity.

        Returns session data dict with token/cookies or error.
        """
        existing = self._get_active_session(identity_id)
        if existing and existing.get("is_valid"):
            # Check expiry
            expires_at = existing.get("expires_at")
            if expires_at and expires_at > datetime.now(timezone.utc):
                return self._session_to_auth_context(existing)
            if expires_at is None:
                return self._session_to_auth_context(existing)

        # Need to login or refresh
        return self._login_and_create_session(identity_id)

    def login(self, identity_id: int) -> dict:
        """Force a fresh login for the given identity."""
        return self._login_and_create_session(identity_id)

    def get_session_status(self, identity_id: int) -> dict:
        session = db.SessionLocal()
        try:
            sess = session.query(models.TargetSession).filter(
                models.TargetSession.identity_id == identity_id
            ).first()
            if not sess:
                return {"identity_id": identity_id, "is_valid": False, "expires_at": None, "last_refresh_at": None, "failure_count": 0}
            return {
                "identity_id": identity_id,
                "is_valid": sess.is_valid,
                "expires_at": sess.expires_at.isoformat() if sess.expires_at else None,
                "last_refresh_at": sess.last_refresh_at.isoformat() if sess.last_refresh_at else None,
                "failure_count": sess.failure_count,
            }
        finally:
            session.close()

    def invalidate_session(self, identity_id: int) -> None:
        session = db.SessionLocal()
        try:
            session.query(models.TargetSession).filter(
                models.TargetSession.identity_id == identity_id
            ).update({"is_valid": False})
            session.commit()
        finally:
            session.close()

    def get_auth_context(self, identity_id: int) -> dict | None:
        """Return AuthContext-compatible dict for the validation replayer.

        Returns None if no valid session available.
        """
        result = self.ensure_session(identity_id)
        if result.get("error"):
            return None
        return result

    # ── Internal ───────────────────────────────────────────────────

    def _get_active_session(self, identity_id: int) -> dict | None:
        session = db.SessionLocal()
        try:
            sess = session.query(models.TargetSession).filter(
                models.TargetSession.identity_id == identity_id
            ).first()
            if not sess:
                return None
            return {
                "id": sess.id,
                "identity_id": sess.identity_id,
                "is_valid": sess.is_valid,
                "expires_at": sess.expires_at,
                "token": self._vault.decrypt(sess.token_encrypted) if sess.token_encrypted else None,
                "cookies": self._vault.decrypt_json(sess.cookies_encrypted) if sess.cookies_encrypted else None,
                "failure_count": sess.failure_count,
            }
        finally:
            session.close()

    def _login_and_create_session(self, identity_id: int) -> dict:
        creds = self._identity_manager.get_decrypted_credentials(identity_id)
        if not creds:
            return {"token": None, "cookies": None, "expires_at": None, "error": "No credentials configured for this identity"}

        # Get identity info
        session = db.SessionLocal()
        try:
            identity = session.query(models.TargetIdentity).filter(
                models.TargetIdentity.id == identity_id,
                models.TargetIdentity.is_active,
            ).first()
            if not identity:
                return {"token": None, "cookies": None, "expires_at": None, "error": "Identity not found or inactive"}

            auth_type = identity.auth_type
        finally:
            session.close()

        # Perform login
        result = self._login_service.login(auth_type, creds)
        if result.get("error"):
            self._record_failure(identity_id)
            return result

        token = result.get("token")
        cookies = result.get("cookies")
        expires_at = result.get("expires_at")

        # Persist session
        self._save_session(identity_id, token, cookies, expires_at)
        return self._session_to_auth_context({
            "is_valid": True,
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc) if expires_at else None,
            "token": token,
            "cookies": cookies,
        })

    def _save_session(
        self,
        identity_id: int,
        token: str | None,
        cookies: dict | None,
        expires_at: float | None,
    ) -> None:
        session = db.SessionLocal()
        try:
            existing = session.query(models.TargetSession).filter(
                models.TargetSession.identity_id == identity_id
            ).first()

            token_encrypted = self._vault.encrypt(token) if token else ""
            cookies_encrypted = self._vault.encrypt_json(cookies) if cookies else ""
            expires_dt = datetime.fromtimestamp(expires_at, tz=timezone.utc) if expires_at else None
            now = datetime.now(timezone.utc)

            if existing:
                existing.token_encrypted = token_encrypted
                existing.cookies_encrypted = cookies_encrypted
                existing.expires_at = expires_dt
                existing.last_refresh_at = now
                existing.is_valid = True
                existing.failure_count = 0
            else:
                new_session = models.TargetSession(
                    identity_id=identity_id,
                    token_encrypted=token_encrypted,
                    cookies_encrypted=cookies_encrypted,
                    expires_at=expires_dt,
                    last_refresh_at=now,
                    is_valid=True,
                    failure_count=0,
                )
                session.add(new_session)
            session.commit()
        except Exception as exc:
            logger.error("Failed to save session: %s", exc)
            session.rollback()
        finally:
            session.close()

    def _record_failure(self, identity_id: int) -> None:
        session = db.SessionLocal()
        try:
            sess = session.query(models.TargetSession).filter(
                models.TargetSession.identity_id == identity_id
            ).first()
            if sess:
                sess.failure_count = (sess.failure_count or 0) + 1
                if sess.failure_count >= 5:
                    sess.is_valid = False
                session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    @staticmethod
    def _session_to_auth_context(session_data: dict) -> dict:
        """Convert session data to AuthContext-compatible dict."""
        return {
            "token": session_data.get("token"),
            "cookies": session_data.get("cookies") or {},
            "label": "authenticated",
            "expires_at": session_data.get("expires_at"),
        }


_session_manager_instance: TargetSessionManager | None = None


def get_session_manager() -> TargetSessionManager:
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = TargetSessionManager()
    return _session_manager_instance
