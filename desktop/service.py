"""Windows Service — registers ORION as a background Windows Service.

Usage:
    python -m desktop.service --install     # Register service
    python -m desktop.service --remove      # Unregister service
    python -m desktop.service --debug       # Run in console (for testing)

The service runs the same backend as desktop mode (uvicorn, agents, scheduler,
eventbus) but without any UI — no window, no tray, no browser.

Architecture:
  - Uses pywin32 (win32serviceutil.ServiceFramework)
  - Runs uvicorn in-process in a daemon thread (same as desktop mode)
  - Watchdog thread monitors health
  - Graceful shutdown on SVC_STOP
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("orion.service")

_pywin32 = {}

try:
    import win32event
    _pywin32["event"] = win32event
except ImportError:
    _pywin32["event"] = None

try:
    import win32service
    _pywin32["service"] = win32service
except ImportError:
    _pywin32["service"] = None

try:
    import win32serviceutil
    _pywin32["serviceutil"] = win32serviceutil
except ImportError:
    _pywin32["serviceutil"] = None

_HAS_PYWIN32 = all(v is not None for v in _pywin32.values())


SERVICE_NAME = "Orion"
SERVICE_DISPLAY_NAME = "ORION Investigation OS"
SERVICE_DESCRIPTION = "Automated security investigation platform"


if _HAS_PYWIN32:

    class OrionService(_pywin32["serviceutil"].ServiceFramework):
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = SERVICE_DISPLAY_NAME
        _svc_description_ = SERVICE_DESCRIPTION

        def __init__(self, args):
            super().__init__(args)
            self._stop_event = _pywin32["event"].CreateEvent(None, 0, 0, None)
            self._server = None
            self._watchdog = None
            self._running = False

        def SvcDoRun(self):
            logger.info("[SERVICE] Starting ORION Service...")
            self._running = True
            self._run_backend()

        def SvcStop(self):
            logger.info("[SERVICE] Stop requested")
            self._running = False
            self.ReportServiceStatus(_pywin32["service"].SERVICE_STOP_PENDING)
            if self._server:
                self._server.stop()
            if self._watchdog:
                self._watchdog.stop()
            _pywin32["event"].SetEvent(self._stop_event)

        def _run_backend(self):
            from api.main import app as api_app
            from desktop.main_desktop import (
                ServerThread,
                _init_settings,
                _lifecycle,
                _mount_frontend,
                _setup_logging,
            )

            _setup_logging(dev=False)
            _lifecycle("[SERVICE]", "ORION Service — PID: %d", os.getpid())

            os.environ["ORION_DESKTOP"] = "1"
            from core_engines.platform.system import get_db_path
            db_path = get_db_path()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
            os.environ["ORION_BASE_DIR"] = str(
                getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)
            )

            port = _init_settings()
            host = "127.0.0.1"

            _mount_frontend(api_app)

            self._server = ServerThread(host=host, port=port)
            self._server.start(api_app)
            _lifecycle("[SERVICE]", "Server started on %s:%d", host, port)

            from desktop.watchdog import Watchdog
            self._watchdog = Watchdog(
                health_check_url=f"http://{host}:{port}/api/health",
                check_interval=30.0,
                max_recovery_attempts=5,
            )
            self._watchdog.start()
            _lifecycle("[SERVICE]", "Watchdog started")

            from core_engines.agents import start_all_agents
            start_all_agents()
            _lifecycle("[SERVICE]", "Agents started")

            _lifecycle("[SERVICE]", "ORION Service is running")

            while self._running:
                _pywin32["event"].WaitForSingleObject(self._stop_event, 5000)

            _lifecycle("[SERVICE]", "Service shutdown complete")
else:

    class OrionService:
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = SERVICE_DISPLAY_NAME
        _svc_description_ = SERVICE_DESCRIPTION

        def __init__(self, args):
            raise RuntimeError("pywin32 not available — cannot run service")

        def SvcDoRun(self):
            raise RuntimeError("pywin32 not available — cannot run service")

        def SvcStop(self):
            raise RuntimeError("pywin32 not available — cannot run service")


def install_service() -> None:
    if not _HAS_PYWIN32:
        print("pywin32 not available — cannot install service")
        print("Install: pip install pywin32")
        sys.exit(1)
    win32serviceutil = _pywin32["serviceutil"]
    print(f"Installing service: {SERVICE_NAME}")
    sys.argv = ["service.py", "--startup", "auto", "install"]
    win32serviceutil.HandleCommandLine(OrionService)
    print(f"Service {SERVICE_NAME} installed and set to auto-start")


def remove_service() -> None:
    if not _HAS_PYWIN32:
        print("pywin32 not available — cannot remove service")
        sys.exit(1)
    win32serviceutil = _pywin32["serviceutil"]
    print(f"Removing service: {SERVICE_NAME}")
    sys.argv = ["service.py", "remove"]
    win32serviceutil.HandleCommandLine(OrionService)
    print(f"Service {SERVICE_NAME} removed")


def run_service() -> None:
    if not _HAS_PYWIN32:
        print("pywin32 not available — running in console mode")
        from desktop.main_desktop import main as desktop_main
        desktop_main()
        return
    win32serviceutil = _pywin32["serviceutil"]
    win32serviceutil.HandleCommandLine(OrionService)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--install":
            install_service()
        elif sys.argv[1] == "--remove":
            remove_service()
        elif sys.argv[1] == "--debug":
            run_service()
        else:
            print("Usage: python -m desktop.service [--install|--remove|--debug]")
    else:
        run_service()
