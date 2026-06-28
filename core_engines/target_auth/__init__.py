"""Target authentication management — identities, credentials, sessions.

Phased replacement for the weak XOR-based identity_vault.
Uses AES-256-GCM for all credential encryption at rest.
"""

from core_engines.target_auth.identity_manager import TargetIdentityManager
from core_engines.target_auth.login_service import TargetLoginService
from core_engines.target_auth.session_manager import TargetSessionManager
from core_engines.target_auth.session_resolver import SessionResolver
from core_engines.target_auth.vault import CredentialVault

__all__ = [
    "CredentialVault",
    "TargetIdentityManager",
    "TargetLoginService",
    "TargetSessionManager",
    "SessionResolver",
]
