"""License validation system for Rastro.

Keys are signed with HMAC-SHA256 using a shared secret embedded in the binary.
In a production deployment, replace with asymmetric crypto (Ed25519) where the
public key is embedded and the private key lives on the licensing server.
"""

from core_engines.license.validator import validate_license, is_license_valid
from core_engines.license.store import get_license_store, LicenseStore
from core_engines.license.hardware import get_hardware_id
