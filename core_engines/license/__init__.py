"""License validation system for Rastro.

Keys are signed with HMAC-SHA256 using a shared secret embedded in the binary.
In a production deployment, replace with asymmetric crypto (Ed25519) where the
public key is embedded and the private key lives on the licensing server.
"""

from core_engines.license.hardware import get_hardware_id
from core_engines.license.store import LicenseStore, get_license_store
from core_engines.license.validator import is_license_valid, validate_license
