from __future__ import annotations

import json
import logging
from typing import Any

from database import db, models
from core_engines.target_auth.vault import get_credential_vault

logger = logging.getLogger("rastro.target_auth.identity")

# Fields stored inside the encrypted credentials JSON blob
CREDENTIAL_FIELDS = frozenset({
    "username", "password", "token", "api_key",
    "cookies", "login_url", "login_params",
})


class TargetIdentityManager:
    """CRUD for target identities with encrypted credential storage."""

    def __init__(self) -> None:
        self._vault = get_credential_vault()

    # ── Public API ─────────────────────────────────────────────────

    def create_identity(
        self,
        target_id: int,
        label: str = "Default",
        auth_type: str = "none",
        is_baseline: bool = False,
        **credential_fields: Any,
    ) -> dict:
        credentials = {k: v for k, v in credential_fields.items() if k in CREDENTIAL_FIELDS and v is not None}
        encrypted = self._vault.encrypt_json(credentials) if credentials else ""

        session = db.SessionLocal()
        try:
            identity = models.TargetIdentity(
                target_id=target_id,
                label=label,
                auth_type=auth_type,
                credentials_encrypted=encrypted,
                is_baseline=is_baseline,
                is_active=True,
            )
            session.add(identity)
            session.flush()

            # If setting as baseline, unset others
            if is_baseline:
                session.query(models.TargetIdentity).filter(
                    models.TargetIdentity.target_id == target_id,
                    models.TargetIdentity.id != identity.id,
                ).update({"is_baseline": False})

            session.commit()
            session.refresh(identity)
            return self._to_out(identity)
        finally:
            session.close()

    def get_identities(self, target_id: int) -> list[dict]:
        session = db.SessionLocal()
        try:
            identities = (
                session.query(models.TargetIdentity)
                .filter(
                    models.TargetIdentity.target_id == target_id,
                    models.TargetIdentity.is_active == True,
                )
                .order_by(models.TargetIdentity.id)
                .all()
            )
            return [self._to_out(identity, session) for identity in identities]
        finally:
            session.close()

    def get_identity(self, identity_id: int) -> dict | None:
        session = db.SessionLocal()
        try:
            identity = session.query(models.TargetIdentity).filter(
                models.TargetIdentity.id == identity_id
            ).first()
            if not identity:
                return None
            return self._to_out(identity, session)
        finally:
            session.close()

    def update_identity(self, identity_id: int, **updates: Any) -> dict | None:
        credential_fields = {k: v for k, v in updates.items() if k in CREDENTIAL_FIELDS}
        direct_fields = {k: v for k, v in updates.items() if k not in CREDENTIAL_FIELDS}

        session = db.SessionLocal()
        try:
            identity = session.query(models.TargetIdentity).filter(
                models.TargetIdentity.id == identity_id
            ).first()
            if not identity:
                return None

            # Update direct columns
            for key, value in direct_fields.items():
                if hasattr(identity, key):
                    setattr(identity, key, value)

            # Update encrypted credentials
            if credential_fields:
                existing_raw = self._vault.decrypt_json(identity.credentials_encrypted or "")
                existing_raw.update(credential_fields)
                # Remove None values
                existing_raw = {k: v for k, v in existing_raw.items() if v is not None}
                identity.credentials_encrypted = self._vault.encrypt_json(existing_raw) if existing_raw else ""

            # Handle baseline toggle
            if updates.get("is_baseline"):
                session.query(models.TargetIdentity).filter(
                    models.TargetIdentity.target_id == identity.target_id,
                    models.TargetIdentity.id != identity_id,
                ).update({"is_baseline": False})

            session.commit()
            session.refresh(identity)
            return self._to_out(identity, session)
        finally:
            session.close()

    def delete_identity(self, identity_id: int) -> bool:
        session = db.SessionLocal()
        try:
            identity = session.query(models.TargetIdentity).filter(
                models.TargetIdentity.id == identity_id
            ).first()
            if not identity:
                return False
            # Soft delete
            identity.is_active = False
            # Also invalidate any active session
            session.query(models.TargetSession).filter(
                models.TargetSession.identity_id == identity_id
            ).update({"is_valid": False})
            session.commit()
            return True
        finally:
            session.close()

    def get_decrypted_credentials(self, identity_id: int) -> dict:
        """Retrieve decrypted credentials for internal use (never expose via API)."""
        session = db.SessionLocal()
        try:
            identity = session.query(models.TargetIdentity).filter(
                models.TargetIdentity.id == identity_id,
                models.TargetIdentity.is_active == True,
            ).first()
            if not identity or not identity.credentials_encrypted:
                return {}
            return self._vault.decrypt_json(identity.credentials_encrypted)
        finally:
            session.close()

    # ── Helpers ────────────────────────────────────────────────────

    def _to_out(self, identity: models.TargetIdentity, db_session=None) -> dict:
        """Convert model to safe output dict (no credentials exposed)."""
        session_valid = False
        session_expires_at = None
        if db_session:
            sess = db_session.query(models.TargetSession).filter(
                models.TargetSession.identity_id == identity.id
            ).first()
            if sess:
                session_valid = sess.is_valid
                session_expires_at = sess.expires_at.isoformat() if sess.expires_at else None

        return {
            "id": identity.id,
            "target_id": identity.target_id,
            "label": identity.label,
            "auth_type": identity.auth_type,
            "is_baseline": identity.is_baseline,
            "is_active": identity.is_active,
            "session_valid": session_valid,
            "session_expires_at": session_expires_at,
            "created_at": identity.created_at.isoformat() if identity.created_at else None,
        }


_identity_manager_instance: TargetIdentityManager | None = None


def get_identity_manager() -> TargetIdentityManager:
    global _identity_manager_instance
    if _identity_manager_instance is None:
        _identity_manager_instance = TargetIdentityManager()
    return _identity_manager_instance
