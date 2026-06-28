from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

logger = logging.getLogger("rastro.settings")

RASTRO_NS = "rastro"
PLATFORM_NS = "platform"


class RastroMode(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


PLATFORM_IDS = ["hackerone", "bugcrowd", "intigriti", "yeswehack", "synack"]

DEFAULT_PLATFORM_CONFIG: dict[str, Any] = {
    "enabled": False,
    "action": "prepare_only",
    "username": "",
    "api_key": "",
}

DEFAULT_PLATFORMS: dict[str, dict[str, Any]] = {
    pid: dict(DEFAULT_PLATFORM_CONFIG) for pid in PLATFORM_IDS
}


def _get_session():
    from database.db import SessionLocal
    return SessionLocal()


def _get_setting(key: str, default: Any = None) -> Any:
    from database.models import RastroConfig
    session = _get_session()
    try:
        record = session.query(RastroConfig).filter(RastroConfig.key == key).first()
        if record:
            return json.loads(record.value)
        return default
    except Exception as exc:
        logger.warning("Failed to read setting %s: %s", key, exc)
        return default
    finally:
        session.close()


def _set_setting(key: str, value: Any) -> None:
    from database.models import RastroConfig
    session = _get_session()
    try:
        record = session.query(RastroConfig).filter(RastroConfig.key == key).first()
        if record:
            record.value = json.dumps(value, ensure_ascii=False)
        else:
            record = RastroConfig(key=key, value=json.dumps(value, ensure_ascii=False))
            session.add(record)
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error("Failed to save setting %s: %s", key, exc)
    finally:
        session.close()


def get_setting(key: str, default: Any = None) -> Any:
    return _get_setting(key, default)


def set_setting(key: str, value: Any) -> None:
    _set_setting(key, value)


def get_mode() -> RastroMode:
    raw = _get_setting(f"{RASTRO_NS}.mode", "manual")
    try:
        return RastroMode(raw)
    except ValueError:
        return RastroMode.MANUAL


def set_mode(mode: str | RastroMode) -> None:
    if isinstance(mode, str):
        mode = RastroMode(mode)
    _set_setting(f"{RASTRO_NS}.mode", mode.value)


def get_platform_config(platform_id: str) -> dict[str, Any]:
    if platform_id not in PLATFORM_IDS:
        return dict(DEFAULT_PLATFORM_CONFIG)
    raw = _get_setting(f"{PLATFORM_NS}.{platform_id}", None)
    if raw is None:
        return dict(DEFAULT_PLATFORM_CONFIG)
    return {**DEFAULT_PLATFORM_CONFIG, **raw}


def set_platform_config(platform_id: str, config: dict[str, Any]) -> None:
    if platform_id not in PLATFORM_IDS:
        raise ValueError(f"Unknown platform: {platform_id}")
    existing = get_platform_config(platform_id)
    existing.update(config)
    _set_setting(f"{PLATFORM_NS}.{platform_id}", existing)


def get_all_platform_configs() -> dict[str, dict[str, Any]]:
    configs = {}
    for pid in PLATFORM_IDS:
        configs[pid] = get_platform_config(pid)
    return configs


def get_all_settings() -> dict[str, Any]:
    return {
        "mode": get_mode().value,
        "platforms": get_all_platform_configs(),
    }
