"""Rastro Desktop — single executable entry point (Windows primary).

Architecture:
  - Backend runs IN-PROCESS (no child processes, no multi-processing).
  - Frontend assets served directly by the backend (no separate server).
  - No process supervisor, no restart loops.
  - Optional system tray (never blocks startup).
  - Primary target: Windows 11. Also works on macOS and Linux (unmaintained).

Startup:
  BOOT → Set env vars → Start API (in-process uvicorn) → Mount frontend on API
  → Wait healthy → Open browser → System tray → Event loop

Shutdown:
  SIGINT/SIGTERM/tray quit → Stop uvicorn → Dispose DB → Stop tray → Exit

PyInstaller produces: dist/Rastro/Rastro  (or dist/Rastro.exe on Windows)
"""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import webview

_BOOT = "[BOOT]"
_API = "[API]"
_FRONTEND = "[FRONTEND]"
_HEALTHY = "[HEALTHY]"
_BROWSER = "[BROWSER]"
_TRAY = "[TRAY]"
_READY = "[READY]"
_SHUTDOWN = "[SHUTDOWN]"

logger = logging.getLogger("rastro.desktop")
_lifecycle_logger: Optional[logging.Logger] = None


# ── Logging ──────────────────────────────────────────────────────────

def _setup_logging(dev: bool) -> str:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path.cwd()
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    rastro_log = log_dir / "rastro.log"
    lifecycle_log = log_dir / "lifecycle.log"
    level = logging.DEBUG if dev else logging.INFO

    root = logging.getLogger()
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    fh = logging.handlers.RotatingFileHandler(
        rastro_log, maxBytes=5 * 1024 * 1024, backupCount=3
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    if dev:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter("[Rastro] %(message)s"))
        root.addHandler(sh)

    global _lifecycle_logger
    _lifecycle_logger = logging.getLogger("rastro.desktop.lifecycle")
    _lifecycle_logger.setLevel(logging.INFO)
    _lifecycle_logger.propagate = False
    lh = logging.handlers.RotatingFileHandler(
        lifecycle_log, maxBytes=2 * 1024 * 1024, backupCount=2
    )
    lh.setFormatter(
        logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    lh.setLevel(logging.INFO)
    _lifecycle_logger.addHandler(lh)

    return str(lifecycle_log)


def _lifecycle(tag: str, msg: str, *args) -> None:
    text = msg % args if args else msg
    logger.info("%s %s", tag, text)
    if _lifecycle_logger:
        _lifecycle_logger.info("%s %s", tag, text)


# ── Server thread ────────────────────────────────────────────────────

class ServerThread:
    """Runs uvicorn in a background daemon thread."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._server: Optional[object] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, app) -> None:
        self._thread = threading.Thread(
            target=self._run, args=(app,), daemon=True, name="rastro-server"
        )
        self._thread.start()

    def _run(self, app) -> None:
        import uvicorn
        from uvicorn import Config, Server
        config = Config(
            app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
            log_config=None,
        )
        self._server = Server(config)
        asyncio.run(self._server.serve())

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True


# ── Health helpers ───────────────────────────────────────────────────

def _wait_for_port(host: str, port: int, timeout: float = 15.0) -> bool:
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.3)
    return False


def _wait_for_health(host: str, port: int, timeout: float = 30.0) -> bool:
    import httpx
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(f"http://{host}:{port}/api/health", timeout=2.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


# ── Frontend mounting ────────────────────────────────────────────────

def _mount_frontend(app) -> bool:
    from pathlib import Path
    import logging
    from core.platform.system import get_frontend_dist_dir
    from fastapi.responses import FileResponse, JSONResponse

    dist_dir: Path = get_frontend_dist_dir()
    if not dist_dir.is_dir():
        _lifecycle(_FRONTEND, "Frontend dist not found at %s", dist_dir)
        return False

    index_path = dist_dir / "index.html"
    log = logging.getLogger("rastro.frontend")

    @app.get("/")
    async def serve_root():
        log.info("serve_root called")
        if index_path.is_file():
            log.info("  serving index.html")
            return FileResponse(str(index_path))
        log.info("  404 - index.html not found")
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        log.info("serve_frontend called: full_path=%s", full_path)
        if full_path:
            file_path = dist_dir / full_path
            if file_path.is_file():
                log.info("  serving file: %s", file_path)
                return FileResponse(str(file_path))
        if index_path.is_file():
            log.info("  serving index.html")
            return FileResponse(str(index_path))
        log.info("  404 - nothing found")
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    # Log the number of routes after adding ours
    mount_count = sum(1 for r in app.routes if getattr(r, "path", "") in ("/", "/{full_path:path}"))
    _lifecycle(_FRONTEND, "Frontend mounted from %s (routes: %d)", dist_dir, mount_count)
    return True


# ── Settings / first run ─────────────────────────────────────────────

def _init_settings() -> int:
    from desktop.settings import get_settings
    from desktop.first_run import run_first_time

    settings = get_settings()
    port = settings.get("backend_port", 8000)
    if not (1024 <= port <= 65535):
        port = 8000
    run_first_time(settings)
    settings.record_boot()
    return port


# ── Desktop window ──────────────────────────────────────────────────

def _open_desktop_window(host: str, port: int) -> None:
    url = f"http://{host}:{port}"
    _lifecycle(_BROWSER, "Opening desktop window → %s", url)
    window = webview.create_window(
        "Rastro Investigation OS",
        url=url,
        width=1400,
        height=900,
        resizable=True,
        min_size=(1024, 600),
    )
    window.closed += lambda: _lifecycle(_SHUTDOWN, "Desktop window closed")
    webview.start(storage_path=None)


def _open_browser(port: int) -> None:
    from desktop.settings import get_settings
    from desktop.browser_opener import open_dashboard, build_dashboard_url
    from desktop.notifications import notify_dashboard_ready

    settings = get_settings()
    first_boot = (
        settings.get("first_run_complete")
        and settings.get("onboarding_complete") is not False
    )

    if first_boot:
        ctx: dict = {
            "port": 5173,
            "token": settings.get("session_token"),
            "device_id": settings.get("device_id"),
        }
        tab = settings.get("last_dashboard_tab")
        if tab:
            ctx["tab"] = tab
        tid = settings.get("last_opened_target")
        if tid:
            ctx["target_id"] = int(tid)
        if settings.get("onboarding_complete") is False:
            ctx["onboarding"] = True
        if open_dashboard(**ctx):
            _lifecycle(_BROWSER, "Dashboard opened in browser")
            notify_dashboard_ready()
            return
        _lifecycle(_BROWSER, "Failed to open browser")
    else:
        _lifecycle(_BROWSER, "Dashboard URL: %s", build_dashboard_url(port=port))


# ── Tray (optional, never blocks) ────────────────────────────────────

def _start_tray(server: ServerThread, shutdown_event: threading.Event):
    from desktop.tray import TrayController
    from desktop.browser_opener import open_dashboard
    from desktop.settings import get_settings

    settings = get_settings()

    def on_quit():
        _lifecycle(_SHUTDOWN, "Quit from tray")
        settings.record_shutdown()
        shutdown_event.set()

    try:
        tray = TrayController(
            on_open_dashboard=lambda: open_dashboard(
                port=5173,
                token=settings.get("session_token"),
                device_id=settings.get("device_id"),
                tab=settings.get("last_dashboard_tab"),
                target_id=settings.get("last_opened_target"),
            ),
            on_open_daily_mode=lambda: open_dashboard(
                port=5173, path="/daily",
                token=settings.get("session_token"),
                device_id=settings.get("device_id"),
            ),
            on_restart=lambda: _lifecycle(_BOOT, "Restart not supported in single-process mode"),
            on_check_status=lambda: f"Running on port {server.port}",
            on_quit=on_quit,
        )
        tray.start()
        _lifecycle(_TRAY, "System tray initialized")
        return tray
    except Exception as exc:
        _lifecycle(_TRAY, "Tray init failed (non-fatal): %s", exc)
        return None


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    dev = "--dev" in sys.argv
    no_tray = "--no-tray" in sys.argv
    browser_mode = "--browser" in sys.argv

    _setup_logging(dev)
    _lifecycle(_BOOT, "Rastro Desktop — PID: %d", os.getpid())
    _lifecycle(_BOOT, "Frozen: %s, Python: %s, OS: %s",
               getattr(sys, "frozen", False),
               sys.version.split()[0], sys.platform)

    # ── Set env before imports that read them ────────────────────────
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        db_url = f"sqlite:///{exe_dir}/database/rastro.db"
        base_dir = str(getattr(sys, "_MEIPASS", exe_dir))
    else:
        db_url = "sqlite:///./database/rastro.db"
        base_dir = str(Path.cwd())

    Path(db_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

    if getattr(sys, "frozen", False):
        os.environ["DATABASE_URL"] = db_url
        os.environ["RASTRO_BASE_DIR"] = base_dir
        os.environ["RASTRO_DESKTOP"] = "1"
    else:
        os.environ.setdefault("DATABASE_URL", db_url)
        os.environ.setdefault("RASTRO_BASE_DIR", base_dir)
        os.environ.setdefault("RASTRO_DESKTOP", "1")

    # ── Init settings / first-run ───────────────────────────────────
    port = _init_settings()
    host = "127.0.0.1"
    _lifecycle(_BOOT, "Backend port: %d", port)

    # ── Import app (env must be set first) ───────────────────────────
    _lifecycle(_API, "Starting API server")
    from api.main import app as api_app

    # Mount frontend static assets on the same app
    _mount_frontend(api_app)

    # ── Start uvicorn in background thread ───────────────────────────
    server = ServerThread(host=host, port=port)
    server.start(api_app)
    _lifecycle(_API, "Server thread started on %s:%d", host, port)

    if not _wait_for_port(host, port):
        _lifecycle(_API, "Server failed to bind on %s:%d", host, port)
        sys.exit(1)
    _lifecycle(_API, "Server listening on %s:%d", host, port)

    if not _wait_for_health(host, port):
        _lifecycle(_HEALTHY, "Health check timed out")
        sys.exit(1)
    _lifecycle(_HEALTHY, "Backend healthy on port %d", port)

    # ── UI mode: desktop window or browser ──────────────────────────
    tray = None

    if browser_mode:
        _open_browser(port)

        shutdown_event: threading.Event = threading.Event()

        def _handle_signal(signum, frame):
            if not shutdown_event.is_set():
                _lifecycle(_SHUTDOWN, "Signal %d received", signum)
            shutdown_event.set()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        if not no_tray:
            tray = _start_tray(server, shutdown_event)

        _lifecycle(_READY, "Rastro Desktop ready (browser mode)")

        try:
            shutdown_event.wait()
        except KeyboardInterrupt:
            _lifecycle(_SHUTDOWN, "KeyboardInterrupt")
    else:
        _lifecycle(_READY, "Rastro Desktop ready (desktop window)")
        _open_desktop_window(host, port)

    # ── Graceful shutdown ───────────────────────────────────────────
    _lifecycle(_SHUTDOWN, "Stopping server...")
    server.stop()

    if tray is not None:
        try:
            tray.stop()
        except Exception:
            pass

    try:
        from database.db import engine
        engine.dispose()
    except Exception:
        pass

    _lifecycle(_SHUTDOWN, "Rastro Desktop stopped")


if __name__ == "__main__":
    main()
