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
        pass
    return "unknown-mac"


def _get_raw_machine_ids() -> list[str]:
    """Collect raw machine identifiers from all available sources."""
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
                    raw.append(guid.strip().lower())
        except Exception:
            pass

    if not raw:
        fallback = os.environ.get("HOSTNAME") or os.environ.get("COMPUTERNAME", "unknown")
        raw.append(fallback)

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

    return "|".join(deduped)


def get_hardware_id() -> str:
    hostname = socket.gethostname()
    mac = _get_mac()
    machine_id = _get_machine_id()

    parts = [hostname, mac, machine_id]
    raw = "|".join(parts)

    hwid = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return hwid
