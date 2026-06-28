"""License key validation using HMAC-SHA256.

Key format: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX (25 chars, 5 groups of 5)
Encodes: version(1) + year(2) + month(2) + day(2) + expiry_year(2) + expiry_month(2) + expiry_day(2) + hw_prefix(7) + base32_hmac(5)
Data: 20 chars, Signature: 5 chars → 25 total.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import time

from core_engines.license.hardware import get_hardware_id
from core_engines.license.store import get_license_store

logger = logging.getLogger("rastro.license.validator")

# Signing secret embedded in the binary.
# In production, rotate this per-release and use asymmetric crypto instead.
_LICENSE_SECRET = os.environ.get(
    "RASTRO_LICENSE_SECRET",
    hashlib.sha256(b"rastro-license-secret-v1").hexdigest(),
)

KEY_PATTERN = re.compile(r"^[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$")

BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def _b32_encode(data: bytes) -> str:
    """Custom base32 encoding (no padding)."""
    result = []
    buffer = 0
    bits = 0
    for byte in data:
        buffer = (buffer << 8) | byte
        bits += 8
        while bits >= 5:
            bits -= 5
            result.append(BASE32_ALPHABET[(buffer >> bits) & 0x1F])
    if bits:
        result.append(BASE32_ALPHABET[(buffer << (5 - bits)) & 0x1F])
    return "".join(result)


def _b32_decode(s: str) -> bytes:
    result = bytearray()
    buffer = 0
    bits = 0
    for ch in s.upper():
        if ch not in BASE32_ALPHABET:
            continue
        value = BASE32_ALPHABET.index(ch)
        buffer = (buffer << 5) | value
        bits += 5
        while bits >= 8:
            bits -= 8
            result.append((buffer >> bits) & 0xFF)
    return bytes(result)


def _generate_key_data(hw_id: str, expiry_days: int = 365) -> tuple[str, bytes]:
    now = time.gmtime()
    year = now.tm_year % 100
    month = now.tm_mon
    day = now.tm_mday
    expiry_year = (now.tm_year + (expiry_days // 365)) % 100
    expiry_month = month
    expiry_day = day

    version = 1
    hw_prefix = hw_id[:7].upper()
    data_str = f"{version:01d}{year:02d}{month:02d}{day:02d}{expiry_year:02d}{expiry_month:02d}{expiry_day:02d}{hw_prefix}"
    payload = data_str.encode("ascii")
    return data_str, payload


def _format_key(data_str: str, sig: str) -> str:
    raw = data_str + sig
    groups = [raw[i:i + 5] for i in range(0, len(raw), 5)]
    return "-".join(groups)


def generate_license(expiry_days: int = 365) -> str:
    """Generate a license key for the current machine (for development/testing).

    NOTE: In production, this runs ONLY on the licensing server.
    """
    hw_id = get_hardware_id()
    data_str, payload = _generate_key_data(hw_id, expiry_days)
    sig_raw = hmac.new(_LICENSE_SECRET.encode(), payload, hashlib.sha256).digest()
    sig = _b32_encode(sig_raw)[:5]
    return _format_key(data_str, sig)


def parse_license(key: str) -> dict | None:
    """Parse a license key without verifying signature."""
    clean = key.replace("-", "").upper()
    if len(clean) != 25:
        logger.warning("Invalid license key length: %d", len(clean))
        return None

    data_str = clean[:20]
    sig_str = clean[20:]

    version = int(data_str[0])
    year = 2000 + int(data_str[1:3])
    month = int(data_str[3:5])
    day = int(data_str[5:7])
    exp_year = 2000 + int(data_str[7:9])
    exp_month = int(data_str[9:11])
    exp_day = int(data_str[11:13])
    hw_prefix = data_str[13:20]

    return {
        "version": version,
        "issued": f"{year}-{month:02d}-{day:02d}",
        "expires": f"{exp_year}-{exp_month:02d}-{exp_day:02d}",
        "hardware_prefix": hw_prefix,
        "signature": sig_str,
    }


def verify_license_key(key: str) -> tuple[bool, str]:
    """Verify a license key's signature and expiry.

    Returns (is_valid, reason).
    """
    parsed = parse_license(key)
    if not parsed:
        return False, "Invalid key format"

    clean = key.replace("-", "").upper()
    data_str = clean[:20]
    sig_str = clean[20:]

    payload = data_str.encode("ascii")
    expected_sig = hmac.new(_LICENSE_SECRET.encode(), payload, hashlib.sha256).digest()
    expected_b32 = _b32_encode(expected_sig)[:5]

    if not hmac.compare_digest(sig_str, expected_b32):
        return False, "Invalid signature"

    exp_parts = parsed["expires"].split("-")
    exp_year = int(exp_parts[0])
    exp_month = int(exp_parts[1])
    exp_day = int(exp_parts[2])

    now = time.gmtime()
    current = now.tm_year * 10000 + now.tm_mon * 100 + now.tm_mday
    expiry = exp_year * 10000 + exp_month * 100 + exp_day
    if current > expiry:
        return False, "License has expired"

    return True, "Valid"


def validate_license(license_key: str) -> tuple[bool, str]:
    """Full license validation: signature + hardware binding + expiry.

    Returns (is_valid, reason).
    """
    logger.info("[HW] validate_license: ENTER key (truncated) = %s...", license_key[:12] if len(license_key) > 12 else license_key)
    valid, reason = verify_license_key(license_key)
    logger.info("[HW] validate_license: verify_license_key result = (%s, %s)", valid, reason)
    if not valid:
        logger.info("[HW] validate_license: returning False because verify failed: %s", reason)
        return valid, reason

    store = get_license_store()
    stored = store.load()
    hw_id = get_hardware_id()
    parsed = parse_license(license_key)

    logger.info("[HW] validate_license: stored = %s", stored is not None)
    if stored:
        logger.info("[HW] validate_license: stored.hardware_id = %s", stored.get("hardware_id", ""))
        logger.info("[HW] validate_license: stored.hardware_id[:7] = %s", stored.get("hardware_id", "")[:7])
    logger.info("[HW] validate_license: current hw_id = %s", hw_id)
    logger.info("[HW] validate_license: current hw_id[:7] = %s", hw_id[:7])
    if parsed:
        logger.info("[HW] validate_license: parsed.hardware_prefix = %s", parsed["hardware_prefix"])
    else:
        logger.info("[HW] validate_license: parsed = None (parse_license failed)")

    # First activation: always accept, bind HWID
    if not stored:
        logger.info("[HW] validate_license: FIRST ACTIVATION — saving HWID %s", hw_id)
        store.save(license_key, hw_id)
        logger.info("[HW] validate_license: first activation SUCCESS")
        return True, "Valid"

    # Subsequent runs: verify HW binding
    stored_hw = stored.get("hardware_id", "")
    logger.info("[HW] validate_license: SUBSEQUENT RUN — stored_hw = %s, current_hw = %s", stored_hw, hw_id)
    logger.info("[HW] validate_license: SUBSEQUENT RUN — checking prefix: hw_id[:7]=%s vs parsed.hardware_prefix=%s", hw_id[:7].upper(), parsed["hardware_prefix"] if parsed else "N/A")

    if parsed and not hw_id.upper().startswith(parsed["hardware_prefix"]):
        logger.info("[HW] validate_license: HARDWARE MISMATCH — current prefix %s does not match license prefix %s", hw_id[:7].upper(), parsed["hardware_prefix"])
        return False, "Hardware mismatch"

    logger.info("[HW] validate_license: prefix check PASSED")

    if stored_hw != hw_id:
        logger.info("[HW] validate_license: stored_hw differs from current — auto-updating binding to %s", hw_id)
        store.save(license_key, hw_id)
    else:
        logger.info("[HW] validate_license: stored_hw == current_hw, no update needed")

    logger.info("[HW] validate_license: returning VALID")
    return True, "Valid"


def is_license_valid() -> tuple[bool, str]:
    """Check if a valid license is already activated on this machine."""
    logger.info("[HW] is_license_valid: ENTER")
    store = get_license_store()
    stored = store.load()
    if not stored:
        logger.info("[HW] is_license_valid: returning False — no license activated")
        return False, "No license activated"
    logger.info("[HW] is_license_valid: stored license found, delegating to validate_license")
    result = validate_license(stored["license_key"])
    logger.info("[HW] is_license_valid: result = (%s, %s)", result[0], result[1])
    return result
