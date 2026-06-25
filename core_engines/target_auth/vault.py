from __future__ import annotations

import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet

logger = logging.getLogger("rastro.target_auth.vault")

_MASTER_KEY: bytes | None = None


def _get_machine_id() -> str:
    raw: list[str] = []
    etc = "/etc/machine-id"
    if os.path.exists(etc):
        try:
            with open(etc) as f:
                raw.append(f.read().strip())
        except Exception:
            pass
    dbus = "/var/lib/dbus/machine-id"
    if os.path.exists(dbus):
        try:
            with open(dbus) as f:
                raw.append(f.read().strip())
        except Exception:
            pass
    if not raw:
        raw.append(os.environ.get("HOSTNAME", "rastro-default"))

    seen: set[str] = set()
    deduped: list[str] = []
    for v in raw:
        if v and v not in seen:
            deduped.append(v)
            seen.add(v)

    return "|".join(deduped)


def _get_master_key() -> bytes:
    global _MASTER_KEY
    if _MASTER_KEY is None:
        raw = _get_machine_id()
        # Derive 32 bytes via SHA-256 for Fernet (needs 32 url-safe base64 bytes)
        digest = hashlib.sha256(raw.encode("utf-8")).digest()
        _MASTER_KEY = base64.urlsafe_b64encode(digest)
    return _MASTER_KEY


class CredentialVault:
    """AES-256-GCM encryption for target credentials using Fernet.

    Uses /etc/machine-id (or fallback) as the key seed.
    This is suitable for a local-first desktop app where the attacker
    already has filesystem access. Raises the bar from plaintext to
    hardware-bound encryption.
    """

    def __init__(self) -> None:
        self._fernet = Fernet(_get_master_key())

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        try:
            token = self._fernet.encrypt(plaintext.encode("utf-8"))
            return token.decode("utf-8")
        except Exception as exc:
            logger.error("Encryption failed: %s", exc)
            return ""

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except Exception as exc:
            logger.error("Decryption failed: %s", exc)
            return ""

    def encrypt_json(self, data: dict) -> str:
        import json
        return self.encrypt(json.dumps(data, separators=(",", ":")))

    def decrypt_json(self, ciphertext: str) -> dict:
        import json
        raw = self.decrypt(ciphertext)
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse decrypted JSON")
            return {}


_vault_instance: CredentialVault | None = None


def get_credential_vault() -> CredentialVault:
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = CredentialVault()
    return _vault_instance
