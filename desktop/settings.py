"""Desktop Settings — persistent JSON configuration for the launcher.

Stores: backend port, auto-start, theme, language, last URL, window state,
uptime history, crash/recovery counts, diagnostic data.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger("rastro.desktop.settings")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "backend_port": 8000,
    "auto_start": False,
    "auto_update": True,
    "silent": False,
    "theme": "detective_dark",
    "language": "en",
    "last_url": "/",
    "last_session_url": None,
    "last_opened_target": None,
    "last_dashboard_tab": None,
    "last_active_filters": {},
    "window": {
        "x": None,
        "y": None,
    },
    "notifications": {
        "enabled": True,
        "new_opportunity": True,
        "system_warning": True,
    },
    "device_id": None,
    "session_token": None,
    "refresh_token": None,
    "first_run": True,
    "onboarding_complete": False,
    "initial_boot_timestamp": None,
    "installed_version": "0.4.0",
    "uptime_history": [],
    "crash_count": 0,
    "recovery_count": 0,
    "last_session": None,
}


def _get_config_path() -> Path:
    from core_engines.platform.system import get_config_dir
    return get_config_dir()


def _get_settings_path() -> Path:
    return _get_config_path() / "settings.json"


class DesktopSettings:
    """Persistent desktop configuration manager."""

    def __init__(self) -> None:
        self._path = str(_get_settings_path())
        self._data: Dict[str, Any] = dict(DEFAULT_SETTINGS)
        self._ensure_config_dir()
        self._load()

    def _ensure_config_dir(self) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        if Path(self._path).exists():
            try:
                with open(self._path) as f:
                    loaded = json.load(f)
                merged = dict(DEFAULT_SETTINGS)
                merged.update(loaded)
                self._data = merged
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load settings: %s", exc)

    def save(self) -> None:
        self._ensure_config_dir()
        try:
            with open(self._path, "w") as f:
                json.dump(self._data, f, indent=2, default=str)
        except OSError as exc:
            logger.warning("Failed to save settings: %s", exc)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
        return val if val is not None else default

    def set(self, key: str, value: Any) -> None:
        keys = key.split(".")
        target = self._data
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save()

    def get_all(self) -> Dict[str, Any]:
        return dict(self._data)

    def reset(self) -> None:
        self._data = dict(DEFAULT_SETTINGS)
        self._data["first_run"] = False
        self.save()

    def record_boot(self) -> None:
        """Record a boot timestamp and mark first run as handled."""
        now = datetime.now(timezone.utc).isoformat()
        if self.get("initial_boot_timestamp") is None:
            self.set("initial_boot_timestamp", now)
        if self.get("first_run", True):
            self.set("first_run", False)
        history = self.get("uptime_history", [])
        history.append({"boot": now, "pid": os.getpid()})
        if len(history) > 100:
            history = history[-100:]
        self._data["uptime_history"] = history
        self.save()

    def record_crash(self) -> None:
        count = self.get("crash_count", 0) + 1
        self.set("crash_count", count)

    def record_recovery(self) -> None:
        count = self.get("recovery_count", 0) + 1
        self.set("recovery_count", count)

    def ensure_device_id(self) -> str:
        """Get or generate a stable device identifier."""
        did = self.get("device_id")
        if not did:
            import platform
            host = platform.node() or "unknown"
            did = f"{host}-{uuid.uuid4().hex[:8]}"
            self.set("device_id", did)
        return did

    def set_auth_tokens(self, session_token: str, refresh_token: str) -> None:
        self.set("session_token", session_token)
        self.set("refresh_token", refresh_token)

    def clear_auth_tokens(self) -> None:
        self.set("session_token", None)
        self.set("refresh_token", None)

    def record_shutdown(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.set("last_session", {
            "shutdown": now,
            "uptime_history_count": len(self.get("uptime_history", [])),
        })

    @property
    def config_path(self) -> str:
        return os.path.dirname(self._path)


_SETTINGS_INSTANCE: Optional[DesktopSettings] = None


def get_settings() -> DesktopSettings:
    global _SETTINGS_INSTANCE
    if _SETTINGS_INSTANCE is None:
        _SETTINGS_INSTANCE = DesktopSettings()
    return _SETTINGS_INSTANCE
