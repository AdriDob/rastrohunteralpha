"""Machine fingerprint for hardware-bound licensing."""

from __future__ import annotations

import hashlib
import logging
import os
import socket

logger = logging.getLogger("rastro.license.hardware")


def _get_mac() -> str:
    try:
        import uuid
        mac = uuid.getnode()
        if mac and (mac >> 40) & 1 == 0:
            return ":".join(f"{(mac >> (8 * i)) & 0xff:02x}" for i in range(6))
    except Exception:
        logger.warning("Failed to get MAC address", exc_info=True)
    return "unknown-mac"


def _get_raw_machine_ids() -> list[str]:
    """Collect raw machine identifiers from all available sources."""
    raw: list[str] = []

    etc = "/etc/machine-id"
    if os.path.exists(etc):
        try:
            with open(etc) as f:
                val = f.read().strip()
                logger.info("[HW] _get_raw_machine_ids: /etc/machine-id = %s", val)
                raw.append(val)
        except Exception:
            logger.info("[HW] _get_raw_machine_ids: /etc/machine-id exists but unreadable")

    dbus = "/var/lib/dbus/machine-id"
    if os.path.exists(dbus):
        try:
            with open(dbus) as f:
                val = f.read().strip()
                logger.info("[HW] _get_raw_machine_ids: /var/lib/dbus/machine-id = %s", val)
                raw.append(val)
        except Exception:
            logger.info("[HW] _get_raw_machine_ids: /var/lib/dbus/machine-id exists but unreadable")

    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            ) as key:
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                if guid:
                    cleaned = guid.strip().lower()
                    logger.info("[HW] _get_raw_machine_ids: Windows MachineGuid = %s", cleaned)
                    raw.append(cleaned)
        except Exception as e:
            logger.info("[HW] _get_raw_machine_ids: Windows MachineGuid error: %s", e)

    if not raw:
        fallback = os.environ.get("HOSTNAME") or os.environ.get("COMPUTERNAME", "unknown")
        logger.info("[HW] _get_raw_machine_ids: No machine-ids found, fallback = %s", fallback)
        raw.append(fallback)

    logger.info("[HW] _get_raw_machine_ids: raw list = %s", raw)
    return raw


def _get_machine_id() -> str:
    raw = _get_raw_machine_ids()

    # Deduplicate: same value may appear from /etc/machine-id and
    # /var/lib/dbus/machine-id on systems where one is a symlink to the other.
    seen: set[str] = set()
    deduped: list[str] = []
    for v in raw:
        if v and v not in seen:
            deduped.append(v)
            seen.add(v)

    result = "|".join(deduped)
    logger.info("[HW] _get_machine_id: deduped = %s", deduped)
    logger.info("[HW] _get_machine_id: result = %s", result)
    return result


def get_hardware_id() -> str:
    hostname = socket.gethostname()
    mac = _get_mac()
    machine_id = _get_machine_id()

    parts = [hostname, mac, machine_id]
    raw = "|".join(parts)
    raw_sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    hwid = raw_sha[:32]

    logger.info("[HW] get_hardware_id: hostname = %s", hostname)
    logger.info("[HW] get_hardware_id: mac = %s", mac)
    logger.info("[HW] get_hardware_id: machine_id = %s", machine_id)
    logger.info("[HW] get_hardware_id: raw_parts = %s", parts)
    logger.info("[HW] get_hardware_id: full_sha256 = %s", raw_sha)
    logger.info("[HW] get_hardware_id: hwid = %s", hwid)
    logger.info("[HW] get_hardware_id: hwid[:7] = %s", hwid[:7])
    return hwid
