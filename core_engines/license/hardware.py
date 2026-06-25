"""Machine fingerprint for hardware-bound licensing."""

from __future__ import annotations

import hashlib
import logging
import os
import socket

logger = logging.getLogger("rastro.license.hardware")

# ─── Diagnostic helper ────────────────────────────────────────

_DIAG_LOG = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "Rastro", "license_diagnostic.log",
)

def _diag(msg: str) -> None:
    try:
        os.makedirs(os.path.dirname(_DIAG_LOG), exist_ok=True)
        with open(_DIAG_LOG, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except Exception:
        pass
    logger.debug("DIAG: %s", msg)

def _diag_box(title: str, msg: str) -> None:
    _diag(f"[MSGBOX] {title}: {msg}")
    import sys
    if getattr(sys, "frozen", False) and os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, msg, title, 0)
        except Exception:
            pass


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
            _diag(f"[HWID-SOURCES] /etc/machine-id EXISTS → added")
        except Exception as e:
            _diag(f"[HWID-SOURCES] /etc/machine-id EXISTS but read failed: {e}")
    else:
        _diag(f"[HWID-SOURCES] /etc/machine-id NOT FOUND (Linux path, expected on Windows)")

    dbus = "/var/lib/dbus/machine-id"
    if os.path.exists(dbus):
        try:
            with open(dbus) as f:
                raw.append(f.read().strip())
            _diag(f"[HWID-SOURCES] /var/lib/dbus/machine-id EXISTS → added")
        except Exception as e:
            _diag(f"[HWID-SOURCES] /var/lib/dbus/machine-id EXISTS but read failed: {e}")
    else:
        _diag(f"[HWID-SOURCES] /var/lib/dbus/machine-id NOT FOUND (Linux path, expected on Windows)")

    if os.name == "nt":
        _diag(f"[HWID-SOURCES] os.name=nt → trying Windows Registry (MachineGuid)")
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
                    _diag(f"[HWID-SOURCES] Registry MachineGuid={guid.strip().lower()}")
                else:
                    _diag(f"[HWID-SOURCES] Registry MachineGuid empty")
        except ImportError:
            _diag(f"[HWID-SOURCES] winreg not available (os.name={os.name})")
        except Exception as e:
            _diag(f"[HWID-SOURCES] Registry read FAILED: {e}")
    else:
        _diag(f"[HWID-SOURCES] os.name={os.name} → NOT Windows, skipping registry")

    if not raw:
        fallback = os.environ.get("HOSTNAME") or os.environ.get("COMPUTERNAME", "unknown")
        _diag(f"[HWID-SOURCES] ALL SOURCES EMPTY → fallback to HOSTNAME/COMPUTERNAME={fallback}")
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

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Raw machine IDs: %s", raw)
        if len(deduped) < len(raw):
            logger.debug("Deduplicated machine IDs: %s (removed %d duplicate(s))", deduped, len(raw) - len(deduped))

    return "|".join(deduped)


def get_hardware_id() -> str:
    hostname = socket.gethostname()
    mac = _get_mac()
    machine_id = _get_machine_id()

    _diag(f"[HWID-CALC] hostname={hostname}")
    _diag(f"[HWID-CALC] mac={mac}")
    _diag(f"[HWID-CALC] os.name={os.name}")
    raw_ids = _get_raw_machine_ids()
    for i, rid in enumerate(raw_ids):
        _diag(f"[HWID-CALC] raw_machine_id[{i}]={rid}")

    parts = [hostname, mac, machine_id]
    raw = "|".join(parts)

    hwid = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    _diag(f"[HWID-CALC] raw_input ({len(raw)} chars)={raw}")
    _diag(f"[HWID-CALC] HWID={hwid}")
    _diag(f"[HWID-CALC] prefix(7)={hwid[:7].upper()}")

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "HWID components: hostname=%s mac=%s machine_id=%s",
            hostname, mac, machine_id,
        )
        logger.debug("HWID raw input (%d chars): %s", len(raw), raw)
        logger.debug("HWID generated: %s (prefix: %s)", hwid, hwid[:7].upper())

    return hwid
