"""Environment Configuration — single source of truth for all env vars.

Centralizes RASTRO_* environment variable reading with defaults,
type coercion, and documentation. Used by desktop, API, and scripts.

Usage:
    from core.env.config import EnvConfig
    cfg = EnvConfig()
    port = cfg.port
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class EnvConfig:
    port: int = field(default_factory=lambda: int(os.environ.get("RASTRO_PORT", "8000")))
    host: str = field(default_factory=lambda: os.environ.get("RASTRO_HOST", "127.0.0.1"))
    desktop: bool = field(default_factory=lambda: os.environ.get("RASTRO_DESKTOP", "0") == "1")
    debug: bool = field(default_factory=lambda: os.environ.get("RASTRO_DEBUG", "0") == "1")
    log_level: str = field(default_factory=lambda: os.environ.get("RASTRO_LOG_LEVEL", "INFO"))
    data_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "RASTRO_DATA_DIR",
                Path.home() / ".local" / "share" / "rastro",
            )
        )
    )
    config_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "RASTRO_CONFIG_DIR",
                Path(
                    os.environ.get(
                        "XDG_CONFIG_HOME",
                        Path.home() / ".config",
                    )
                ) / "rastro",
            )
        )
    )
    frontend_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "RASTRO_FRONTEND_DIR",
                Path(__file__).resolve().parent.parent.parent / "frontend",
            )
        )
    )
    frontend_dist_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "RASTRO_FRONTEND_DIST_DIR",
                Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
            )
        )
    )
    disable_frontend: bool = field(
        default_factory=lambda: os.environ.get("RASTRO_DISABLE_FRONTEND", "0") == "1"
    )
    no_browser: bool = field(
        default_factory=lambda: os.environ.get("RASTRO_NO_BROWSER", "0") == "1"
    )
    max_restart_retries: int = field(
        default_factory=lambda: int(os.environ.get("RASTRO_MAX_RESTART_RETRIES", "3"))
    )
    health_check_interval: int = field(
        default_factory=lambda: int(os.environ.get("RASTRO_HEALTH_CHECK_INTERVAL", "10"))
    )
    build_env: str = field(
        default_factory=lambda: os.environ.get("RASTRO_BUILD_ENV", "production")
    )
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL",
            f"sqlite:///{Path.home() / '.orion' / 'database' / 'orion.db'}",
        )
    )

    @property
    def is_production(self) -> bool:
        return self.build_env == "production"


_CONFIG_INSTANCE: EnvConfig | None = None


def get_config() -> EnvConfig:
    global _CONFIG_INSTANCE
    if _CONFIG_INSTANCE is None:
        _CONFIG_INSTANCE = EnvConfig()
    return _CONFIG_INSTANCE
