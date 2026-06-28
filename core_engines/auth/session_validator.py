"""SessionValidator — validates sessions, enforces expiry, tracks anomalies."""

from __future__ import annotations

import logging
import time
from typing import Any

from core_engines.auth.auth import verify_session
from core_engines.auth.session import get_session_store

logger = logging.getLogger("rastro.auth.session_validator")


class SessionValidationResult:
    def __init__(
        self,
        valid: bool,
        device_id: str | None = None,
        user_id: str | None = None,
        reason: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.valid = valid
        self.device_id = device_id
        self.user_id = user_id
        self.reason = reason
        self.data = data or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "device_id": self.device_id,
            "user_id": self.user_id,
            "reason": self.reason,
            "data": self.data,
        }


class SessionValidator:
    """Validates sessions, enforces expiry, and detects anomalies."""

    MAX_SESSION_AGE = 86400 * 7  # 7 days max
    MAX_INACTIVE_HOURS = 72

    def __init__(self) -> None:
        self._store = get_session_store()
        self._anomalies: list[dict[str, Any]] = []

    def validate(self, token: str, device_id: str | None = None) -> SessionValidationResult:
        valid, data = verify_session(token)
        if not valid:
            self._anomalies.append({
                "type": "invalid_token",
                "device_id": device_id,
                "timestamp": time.time(),
            })
            return SessionValidationResult(
                valid=False, reason="Invalid or expired token"
            )

        sub = data.get("sub", "") if data else ""

        if device_id and sub and sub != device_id:
            self._anomalies.append({
                "type": "device_mismatch",
                "expected": device_id,
                "actual": sub,
                "timestamp": time.time(),
            })
            return SessionValidationResult(
                valid=False,
                device_id=device_id,
                reason="Token device binding mismatch",
            )

        if data:
            iat = data.get("iat", 0) if isinstance(data, dict) else 0
            if iat and (time.time() - iat) > self.MAX_SESSION_AGE:
                return SessionValidationResult(
                    valid=False,
                    device_id=device_id,
                    reason="Session exceeded maximum age",
                )

        session = None
        if sub:
            session = self._store.get_session(sub)

        if session:
            last_seen = session.get("last_seen", 0)
            if last_seen and (time.time() - last_seen) > self.MAX_INACTIVE_HOURS * 3600:
                return SessionValidationResult(
                    valid=False,
                    device_id=sub,
                    reason="Session expired due to inactivity",
                )

        return SessionValidationResult(
            valid=True,
            device_id=sub or device_id,
            user_id="local",
            data={"sub": sub, "has_session": session is not None},
        )

    def validate_device(self, device_id: str) -> bool:
        session = self._store.get_session(device_id)
        if session is None:
            return False
        last_seen = session.get("last_seen", 0)
        return not (last_seen and time.time() - last_seen > self.MAX_INACTIVE_HOURS * 3600)

    def get_anomalies(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._anomalies[-limit:]

    def clear_anomalies(self) -> None:
        self._anomalies.clear()


_VALIDATOR: SessionValidator | None = None


def get_session_validator() -> SessionValidator:
    global _VALIDATOR
    if _VALIDATOR is None:
        _VALIDATOR = SessionValidator()
    return _VALIDATOR
