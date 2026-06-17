"""System Tray — persistent system tray icon using pystray.

Runs in a separate daemon thread. Closing the browser does NOT stop the system.
The tray survives browser closes and provides full system control.

Menu:
  - Open Dashboard
  - Open Daily Mode
  ──────────
  - Restart Services
  - Check Status
  ──────────
  - Quit Rastro
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

logger = logging.getLogger("rastro.desktop.tray")

_HAS_PYSTRAY = False
try:
    import pystray
    from PIL import Image, ImageDraw
    _HAS_PYSTRAY = True
except ImportError:
    pass


def _create_icon_image(size: int = 64) -> "Image.Image":
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = size // 8
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 4,
        fill=(124, 58, 237, 255),
    )
    try:
        draw.text(
            (size // 2, size // 2),
            "R",
            fill=(255, 255, 255, 255),
            anchor="mm",
            font_size=size // 2,
        )
    except Exception:
        cx, cy = size // 2, size // 2
        r = size // 4
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 255))
    return img


class TrayController:
    """Manages the system tray icon lifecycle.

    Closing the browser window does NOT stop the system.
    The tray is the primary user-facing control for Rastro.
    """

    def __init__(
        self,
        on_open_dashboard: Callable[[], Any],
        on_open_daily_mode: Callable[[], Any],
        on_restart: Callable[[], Any],
        on_check_status: Callable[[], str],
        on_quit: Callable[[], Any],
    ) -> None:
        self._on_open_dashboard = on_open_dashboard
        self._on_open_daily_mode = on_open_daily_mode
        self._on_restart = on_restart
        self._on_check_status = on_check_status
        self._on_quit = on_quit
        self._icon: Any = None
        self._thread: Optional[threading.Thread] = None

    def _create_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Open Dashboard", lambda: self._on_open_dashboard()),
            pystray.MenuItem("Open Daily Mode", lambda: self._on_open_daily_mode()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Restart Services", lambda: self._on_restart()),
            pystray.MenuItem(
                "Check Status",
                lambda: self._show_status(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Rastro", lambda: self._on_quit()),
        )

    def _show_status(self) -> None:
        status_text = self._on_check_status()
        if self._icon:
            self._icon.title = f"Rastro — {status_text}"

    def _run(self) -> None:
        if not _HAS_PYSTRAY:
            logger.warning("pystray not installed — tray icon unavailable")
            return

        icon_image = _create_icon_image()
        menu = self._create_menu()
        try:
            self._icon = pystray.Icon("rastro", icon_image, "Rastro - Running", menu)
            self._icon.run()
        except Exception as exc:
            logger.warning("Tray icon failed to start: %s", exc)

    def start(self) -> Optional[threading.Thread]:
        if not _HAS_PYSTRAY:
            logger.info("pystray not installed — running in CLI mode (no tray icon)")
            return None

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="rastro-tray",
        )
        self._thread.start()
        logger.info("System tray started (persistent)")
        return self._thread

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
        self._thread = None
        logger.info("System tray stopped")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()


# ── Legacy compatibility wrapper ────────────────────────────────────

def start_tray_thread(
    on_start: Callable[..., Any],
    on_stop: Callable[..., Any],
    on_restart: Callable[..., Any],
    on_open_dashboard: Callable[..., Any],
    on_exit: Callable[..., Any],
    services_running: bool = False,
) -> Optional[threading.Thread]:
    logger.warning("start_tray_thread is deprecated — use TrayController instead")
    return None
