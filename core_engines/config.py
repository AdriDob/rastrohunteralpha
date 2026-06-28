import os
from dataclasses import dataclass, field


@dataclass
class RastroConfig:
    db_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", "sqlite:///rastro.db"))
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))
    log_json: bool = field(default_factory=lambda: os.environ.get("LOG_JSON", "false").lower() == "true")
    backend_url: str = field(default_factory=lambda: os.environ.get("RASTRO_BACKEND", "http://127.0.0.1:8000"))
    max_endpoints_per_scan: int = int(os.environ.get("MAX_ENDPOINTS_PER_SCAN", "5000"))
    screenshot_enabled: bool = field(default_factory=lambda: os.environ.get("SCREENSHOT_ENABLED", "true").lower() == "true")
    quick_wins_enabled: bool = field(default_factory=lambda: os.environ.get("QUICK_WINS_ENABLED", "true").lower() == "true")
    cache_size: int = int(os.environ.get("CACHE_SIZE", "4096"))


_config: RastroConfig | None = None


def get_config() -> RastroConfig:
    global _config
    if _config is None:
        _config = RastroConfig()
    return _config


def set_config(cfg: RastroConfig) -> None:
    global _config
    _config = cfg
