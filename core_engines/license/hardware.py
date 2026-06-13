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


def _get_machine_id() -> str:
    candidates = []
    etc = "/etc/machine-id"
    if os.path.exists(etc):
        try:
            with open(etc) as f:
                candidates.append(f.read().strip())
        except Exception:
            pass
    dbus = "/var/lib/dbus/machine-id"
    if os.path.exists(dbus):
        try:
            with open(dbus) as f:
                candidates.append(f.read().strip())
        except Exception:
            pass
    if not candidates:
        candidates.append(os.environ.get("HOSTNAME", "unknown"))
    return "|".join(candidates)


def get_hardware_id() -> str:
    parts = [
        socket.gethostname(),
        _get_mac(),
        _get_machine_id(),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
