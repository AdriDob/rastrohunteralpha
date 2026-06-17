from __future__ import annotations

import logging
from typing import Any

from core_engines.target_auth.session_manager import get_session_manager

logger = logging.getLogger("rastro.target_auth.resolver")


class SessionResolver:
    """Resolves an identity_id to an AuthContext for the validation replayer.

    This is the bridge between target_auth and the existing
    validation pipeline (ValidationLoopEngine, RequestReplayer).
    """

    def __init__(self) -> None:
        self._session_manager = get_session_manager()

    def resolve(self, identity_id: int | None) -> dict[str, Any] | None:
        """Resolve identity_id to AuthContext-compatible dict.

        If identity_id is None, returns None (treated as anonymous/unauthenticated).
        If the identity has no valid session, attempts login.
        If login fails, returns None.
        """
        if identity_id is None:
            return None

        ctx = self._session_manager.get_auth_context(identity_id)
        if ctx is None:
            logger.warning("No valid session for identity %d", identity_id)
            return None

        return {
            "token": ctx.get("token"),
            "cookies": ctx.get("cookies", {}),
            "headers": {},
            "label": f"identity_{identity_id}",
        }


_resolver_instance: SessionResolver | None = None


def get_session_resolver() -> SessionResolver:
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = SessionResolver()
    return _resolver_instance
