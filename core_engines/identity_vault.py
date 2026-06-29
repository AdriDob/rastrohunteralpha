"""Identity Vault — secure provider credential management.

Stores encrypted credentials for bug bounty platforms.
Never logs secrets. Never auto-submits reports.
All storage is encrypted at rest using AES-256-GCM.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger("rastro.identity_vault")

_VAULT_PATH: str | None = None
_VAULT_KEY: bytes | None = None
_VAULT_DATA: dict[str, dict[str, Any]] = {}

_AES_NONCE_BYTES = 12


def _get_vault_path() -> str:
    global _VAULT_PATH
    if _VAULT_PATH is None:
        home = os.environ.get("HOME", os.environ.get("USERPROFILE", "."))
        _VAULT_PATH = os.path.join(home, ".orion", "identity_vault.json")
    return _VAULT_PATH


def _get_vault_key() -> bytes:
    global _VAULT_KEY
    if _VAULT_KEY is None:
        machine_id = _get_machine_id()
        _VAULT_KEY = hashlib.sha256(machine_id.encode()).digest()
    return _VAULT_KEY


def _get_machine_id() -> str:
    """Derive a machine-local identifier for encryption."""
    raw: list[str] = []
    etc_machine = "/etc/machine-id"
    if os.path.exists(etc_machine):
        try:
            with open(etc_machine) as f:
                raw.append(f.read().strip())
        except Exception:
            logger.warning("Failed to read /etc/machine-id", exc_info=True)
    if not raw:
        raw.append(os.environ.get("HOSTNAME", "rastro-default"))

    seen: set[str] = set()
    deduped: list[str] = []
    for v in raw:
        if v and v not in seen:
            deduped.append(v)
            seen.add(v)

    return "|".join(deduped)


def _aes_encrypt(plaintext: str, key: bytes) -> str:
    """Encrypt data with AES-256-GCM. Returns base64(nonce + ciphertext + tag)."""
    if not plaintext:
        return ""
    aesgcm = AESGCM(key)
    nonce = os.urandom(_AES_NONCE_BYTES)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def _aes_decrypt(payload: str, key: bytes) -> str:
    """Decrypt data encrypted with AES-256-GCM. Expects base64(nonce + ciphertext + tag)."""
    if not payload:
        return ""
    try:
        raw = base64.b64decode(payload.encode("ascii"))
        if len(raw) < _AES_NONCE_BYTES + 16:
            return ""
        nonce = raw[:_AES_NONCE_BYTES]
        ciphertext = raw[_AES_NONCE_BYTES:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception:
        logger.warning("AES-256-GCM decryption failed — key may have changed")
        return ""


class IdentityVault:
    """Secure credential vault for bug bounty provider accounts."""

    SUPPORTED_PROVIDERS = [
        "hackerone", "bugcrowd", "huntr", "immunefi",
        "intigriti", "yeswehack", "github", "synack",
    ]

    def __init__(self) -> None:
        self._load()

    # ── Public API ─────────────────────────────────────────────────

    def list_accounts(self) -> list[dict[str, Any]]:
        """List all stored accounts (without secrets)."""
        result = []
        for provider, data in _VAULT_DATA.items():
            result.append({
                "provider_name": provider,
                "email": data.get("email", ""),
                "session_state": data.get("session_state", "disconnected"),
                "last_checked": data.get("last_checked"),
                "health_status": data.get("health_status", "unknown"),
                "has_credentials": bool(data.get("encrypted_token") or data.get("encrypted_password")),
            })
        return result

    def get_account(self, provider: str) -> dict[str, Any] | None:
        """Get a specific stored account (without secrets)."""
        data = _VAULT_DATA.get(provider)
        if not data:
            return None
        return {
            "provider_name": provider,
            "email": data.get("email", ""),
            "session_state": data.get("session_state", "disconnected"),
            "last_checked": data.get("last_checked"),
            "health_status": data.get("health_status", "unknown"),
            "has_credentials": bool(data.get("encrypted_token") or data.get("encrypted_password")),
        }

    def store_credentials(
        self,
        provider: str,
        email: str,
        token: str = "",
        password: str = "",
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Store encrypted credentials for a provider."""
        if provider not in self.SUPPORTED_PROVIDERS and provider not in _VAULT_DATA:
            logger.warning("Storing credentials for unsupported provider: %s", provider)

        key = _get_vault_key()
        entry = {
            "email": email,
            "session_state": "disconnected",
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "health_status": "unknown",
            "encrypted_token": _aes_encrypt(token, key) if token else "",
            "encrypted_password": _aes_encrypt(password, key) if password else "",
            "metadata": json.dumps(metadata or {}),
        }

        if provider in _VAULT_DATA:
            existing = _VAULT_DATA[provider]
            entry["session_state"] = existing.get("session_state", "disconnected")
            entry["health_status"] = existing.get("health_status", "unknown")
            if not token:
                entry["encrypted_token"] = existing.get("encrypted_token", "")
            if not password:
                entry["encrypted_password"] = existing.get("encrypted_password", "")

        _VAULT_DATA[provider] = entry
        self._save()
        logger.info("Credentials stored for provider: %s (email: %s)", provider, email)

    def get_credentials(self, provider: str) -> dict[str, str]:
        """Retrieve decrypted credentials. Use sparingly — never log."""
        data = _VAULT_DATA.get(provider)
        if not data:
            return {}

        key = _get_vault_key()
        token = _aes_decrypt(data.get("encrypted_token", ""), key)
        password = _aes_decrypt(data.get("encrypted_password", ""), key)
        metadata_raw = data.get("metadata", "{}")
        try:
            metadata = json.loads(metadata_raw)
        except (json.JSONDecodeError, TypeError):
            metadata = {}

        return {
            "email": data.get("email", ""),
            "token": token,
            "password": password,
            **metadata,
        }

    def remove_credentials(self, provider: str) -> None:
        """Remove stored credentials for a provider."""
        if provider in _VAULT_DATA:
            del _VAULT_DATA[provider]
            self._save()
            logger.info("Credentials removed for provider: %s", provider)

    def update_session_state(self, provider: str, state: str) -> None:
        """Update session connection state."""
        if provider in _VAULT_DATA:
            _VAULT_DATA[provider]["session_state"] = state
            _VAULT_DATA[provider]["last_checked"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def update_health(self, provider: str, status: str) -> None:
        """Update provider health status."""
        if provider in _VAULT_DATA:
            _VAULT_DATA[provider]["health_status"] = status
            _VAULT_DATA[provider]["last_checked"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def check_session_health(self, provider: str) -> dict[str, Any]:
        """Check whether a stored session is still valid."""
        data = _VAULT_DATA.get(provider)
        if not data:
            return {"connected": False, "reason": "No credentials stored"}

        last_checked_str = data.get("last_checked", "")
        last_checked = None
        if last_checked_str:
            with contextlib.suppress(ValueError, TypeError):
                last_checked = datetime.fromisoformat(last_checked_str)

        hours_since_check = 999
        if last_checked:
            hours_since_check = (datetime.now(timezone.utc) - last_checked).total_seconds() / 3600

        state = data.get("session_state", "disconnected")
        has_creds = bool(data.get("encrypted_token") or data.get("encrypted_password"))

        if state == "connected" and hours_since_check < 24 and has_creds:
            return {"connected": True, "reason": "Session appears valid"}
        elif state == "connected" and hours_since_check >= 24:
            return {"connected": False, "reason": "Session may have expired — re-check"}
        else:
            return {"connected": False, "reason": f"State: {state}"}

    def connected_count(self) -> int:
        """Count of providers with active connected sessions."""
        return sum(
            1 for d in _VAULT_DATA.values()
            if d.get("session_state") == "connected"
        )

    def clear_all(self) -> None:
        """Clear all stored credentials."""
        _VAULT_DATA.clear()
        self._save()
        logger.info("Identity vault cleared")

    # ── Persistence ────────────────────────────────────────────────

    def _load(self) -> None:
        path = _get_vault_path()
        if os.path.exists(path):
            try:
                with open(path) as f:
                    loaded = json.load(f)
                _VAULT_DATA.clear()
                _VAULT_DATA.update(loaded)
                logger.info("Loaded identity vault from %s (%d entries)", path, len(_VAULT_DATA))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load identity vault: %s", exc)

    def _save(self) -> None:
        path = _get_vault_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w") as f:
                json.dump(_VAULT_DATA, f, indent=2)
            os.chmod(path, 0o600)  # owner read/write only
        except OSError as exc:
            logger.warning("Failed to save identity vault: %s", exc)


_VAULT_INSTANCE: IdentityVault | None = None


def get_identity_vault() -> IdentityVault:
    global _VAULT_INSTANCE
    if _VAULT_INSTANCE is None:
        _VAULT_INSTANCE = IdentityVault()
    return _VAULT_INSTANCE
