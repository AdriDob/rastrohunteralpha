"""Production Static File Server — serves the built frontend dist.

In production (PyInstaller bundle or release), Vite is not available.
This module provides:
  - mount_frontend(app): Mount frontend dist onto an existing FastAPI app (in-process).
  - create_app(dir): Create a standalone frontend server (legacy).
  - main(): CLI entry point for standalone frontend server.

Usage (in-process, preferred):
    from fastapi import FastAPI
    from desktop.serve_frontend import mount_frontend
    app = FastAPI()
    mount_frontend(app)

Usage (standalone, legacy):
    python -m desktop.serve_frontend [--port PORT] [--dir DIR]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core_engines.platform.system import get_frontend_dist_dir

logger = logging.getLogger("rastro.frontend_server")

DEFAULT_FRONTEND_DIR = str(get_frontend_dist_dir())

def _is_dir(path: str) -> bool:
    return Path(path).is_dir()

app = FastAPI(title="Rastro Frontend")


def mount_frontend(target_app: FastAPI, static_dir: str | None = None) -> bool:
    """Mount frontend static dist onto an existing FastAPI app.

    Args:
        target_app: The FastAPI instance to mount on.
        static_dir: Path to frontend dist directory. Auto-detected if None.

    Returns:
        True if frontend was mounted, False if dist directory not found.
    """
    if static_dir is None:
        static_dir = str(get_frontend_dist_dir())

    if not _is_dir(static_dir):
        logger.warning("Frontend dist not found at %s", static_dir)
        return False

    target_app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    logger.info("Frontend mounted from %s", static_dir)
    return True


def create_app(static_dir: str) -> FastAPI:
    _app = FastAPI(title="Rastro Frontend")

    if not _is_dir(static_dir):
        @_app.get("/{full_path:path}")
        async def not_found(full_path: str):
            return {"error": "Frontend not built — run `npm run build` in frontend/"}

        return _app

    _app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    return _app


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Rastro frontend")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--dir", type=str, default=DEFAULT_FRONTEND_DIR)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="[Rastro] %(message)s",
        stream=sys.stdout,
    )

    if not _is_dir(args.dir):
        logger.warning("Frontend dist not found at %s", args.dir)
        logger.warning("Build it first: cd frontend && npm run build")

    static_app = create_app(args.dir)
    import uvicorn
    uvicorn.run(static_app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
