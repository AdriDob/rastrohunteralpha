"""System Tray — persistent system tray icon using pystray.

Runs in a separate daemon thread. Closing the browser does NOT stop the system.
The tray survives browser closes and provides full system control.

Menu:
  - Open Dashboard
  - Open Daily Mode
  ──────────
  - View Logs
  - Open Data Folder
  ──────────
  - Restart Service
  - Stop Service
  ──────────
  - Check Status
  ──────────
  - Quit Tray
"""

from __future__ import annotations

import contextlib
import logging
import os
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.desktop.tray")

_HAS_PYSTRAY = False
_HAS_ICON_FILE = False
try:
    import pystray
    from PIL import Image, ImageDraw
    _HAS_PYSTRAY = True
except ImportError:
    pass

# ORION brand colors
BG = (10, 11, 15)       # #0a0b0f
GOLD = (212, 175, 55)    # #d4af37
BLUE = (59, 130, 246)    # #3b82f6
TEXT = (248, 250, 252)   # #f8fafc


def _create_icon_image(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2

    # Try to load the branded icon file
    icon_path = _try_find_icon()
    if icon_path:
        try:
            ico = Image.open(icon_path)
            ico = ico.resize((size, size), Image.LANCZOS)
            return ico.convert("RGBA")
        except Exception:
            pass

    # Fallback: draw a gold 'O' ring
    outer_r = size * 0.40
    inner_r = size * 0.20
    for y in range(size):
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if inner_r < dist <= outer_r:
                t = (dist - inner_r) / (outer_r - inner_r)
                r = int(GOLD[0] * (1 - t) + BLUE[0] * t)
                g = int(GOLD[1] * (1 - t) + BLUE[1] * t)
                b = int(GOLD[2] * (1 - t) + BLUE[2] * t)
                draw.point((x, y), fill=(r, g, b, 255))
    return img


def _try_find_icon() -> Path | None:
    for candidate in [
        Path(__file__).resolve().parent.parent / "installer" / "icons" / "orion.ico",
        Path(sys.executable).parent / "orion.ico",
    ]:
        if candidate.exists():
            return candidate
    return None


def _get_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home()
    return base / "Orion"


def _get_logs_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "logs"
    return _get_data_dir() / "logs"


def _open_file_explorer(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception as exc:
        logger.warning("Failed to open file explorer: %s", exc)


def _open_logs_dir() -> None:
    logs_dir = _get_logs_dir()
    if logs_dir.exists():
        _open_file_explorer(logs_dir)
    else:
        data_dir = _get_data_dir()
        if data_dir.exists():
            _open_file_explorer(data_dir)


def _open_data_folder() -> None:
    _open_file_explorer(_get_data_dir())


class TrayController:
    """Manages the system tray icon lifecycle.

    Closing the browser window does NOT stop the system.
    The tray is the primary user-facing control for ORION.
    """

    def __init__(
        self,
        on_open_dashboard: Callable[[], Any],
        on_open_daily_mode: Callable[[], Any],
        on_restart: Callable[[], Any] | None = None,
        on_stop_service: Callable[[], Any] | None = None,
        on_check_status: Callable[[], str] | None = None,
        on_quit: Callable[[], Any] | None = None,
    ) -> None:
        self._on_open_dashboard = on_open_dashboard
        self._on_open_daily_mode = on_open_daily_mode
        self._on_restart = on_restart or (lambda: None)
        self._on_stop_service = on_stop_service or (lambda: None)
        self._on_check_status = on_check_status or (lambda: "Running")
        self._on_quit = on_quit or (lambda: None)
        self._icon: Any = None
        self._thread: threading.Thread | None = None

    def _create_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Open Dashboard", lambda: self._on_open_dashboard()),
            pystray.MenuItem("Open Daily Mode", lambda: self._on_open_daily_mode()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("View Logs", lambda: _open_logs_dir()),
            pystray.MenuItem("Open Data Folder", lambda: _open_data_folder()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Restart Service", lambda: self._on_restart()),
            pystray.MenuItem("Stop Service", lambda: self._on_stop_service()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Check Status",
                lambda: self._show_status(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Tray", lambda: self._on_quit()),
        )

    def _show_status(self) -> None:
        status_text = self._on_check_status()
        if self._icon:
            self._icon.title = f"ORION — {status_text}"

    def _run(self) -> None:
        if not _HAS_PYSTRAY:
            logger.warning("pystray not installed — tray icon unavailable")
            return

        icon_image = _create_icon_image()
        menu = self._create_menu()
        try:
            self._icon = pystray.Icon("orion", icon_image, "ORION - Running", menu)
            self._icon.run()
        except Exception as exc:
            logger.warning("Tray icon failed to start: %s", exc)

    def start(self) -> threading.Thread | None:
        if not _HAS_PYSTRAY:
            logger.info("pystray not installed — running in CLI mode (no tray icon)")
            return None

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="orion-tray",
        )
        self._thread.start()
        logger.info("System tray started (persistent)")
        return self._thread

    def stop(self) -> None:
        if self._icon:
            with contextlib.suppress(Exception):
                self._icon.stop()
            self._icon = None
        self._thread = None
        logger.info("System tray stopped")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()


def run_tray_only(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run tray icon only — no backend, assumes service is already running.

    Opens the dashboard in the browser and shows the tray icon.
    Closing the tray does NOT stop the backend service.
    """
    from desktop.browser_opener import open_dashboard
    from desktop.service_util import is_service_running as _is_svc_running
    from desktop.settings import get_settings

    settings = get_settings()
    token = settings.get("session_token")
    device_id = settings.get("device_id")

    shutdown_event: threading.Event = threading.Event()

    def _open_dashboard():
        open_dashboard(
            port=port,
            token=token,
            device_id=device_id,
            tab=settings.get("last_dashboard_tab"),
        )

    def _open_daily():
        open_dashboard(
            port=port, path="/daily",
            token=token, device_id=device_id,
        )

    def _check_status() -> str:
        if _is_svc_running():
            return f"Service running on port {port}"
        try:
            import httpx
            r = httpx.get(f"http://{host}:{port}/api/health", timeout=3.0)
            return f"OK ({r.status_code})" if r.status_code == 200 else f"HTTP {r.status_code}"
        except Exception as exc:
            return f"Offline ({str(exc)[:40]})"

    def _restart_service():
        try:
            if _is_svc_running():
                subprocess.run(
                    ["net", "stop", "Orion", "&&", "net", "start", "Orion"],
                    shell=True, check=False,
                )
        except Exception:
            pass

    def _stop_service():
        try:
            if _is_svc_running():
                subprocess.run(["net", "stop", "Orion"], shell=True, check=False)
        except Exception:
            pass

    def _quit_tray():
        shutdown_event.set()

    tray = TrayController(
        on_open_dashboard=_open_dashboard,
        on_open_daily_mode=_open_daily,
        on_restart=_restart_service,
        on_stop_service=_stop_service,
        on_check_status=_check_status,
        on_quit=_quit_tray,
    )
    tray.start()

    _open_dashboard()
    logger.info("Tray-only mode — backend assumed running on %s:%d", host, port)

    with contextlib.suppress(KeyboardInterrupt):
        shutdown_event.wait()

    tray.stop()
    logger.info("Tray closed — backend continues running")


# ── Legacy compatibility wrapper ────────────────────────────────────

def start_tray_thread(
    on_start: Callable[..., Any],
    on_stop: Callable[..., Any],
    on_restart: Callable[..., Any],
    on_open_dashboard: Callable[..., Any],
    on_exit: Callable[..., Any],
    services_running: bool = False,
) -> threading.Thread | None:
    logger.warning("start_tray_thread is deprecated — use TrayController instead")
    return None
