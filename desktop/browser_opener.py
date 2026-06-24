"""Browser Opener — detects default browser and opens URLs in the system browser.

Uses Python's stdlib `webbrowser` module. Works cross-platform.
"""

from __future__ import annotations

import logging
import shutil
import urllib.parse
import webbrowser
from typing import Optional

logger = logging.getLogger("rastro.desktop.browser_opener")

# Common browser executable names by priority
BROWSER_NAMES = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "firefox",
    "mozilla-firefox",
    "brave-browser",
    "brave",
    "edge",
    "microsoft-edge",
    "opera",
    "vivaldi",
    "safari",
]


def detect_default_browser() -> Optional[str]:
    """Detect the default system browser name, or None if unknown."""
    # Try webbrowser's own detection first
    try:
        controller = webbrowser.get()
        if controller and controller.name:
            return controller.name
    except Exception:
        pass

    # Fallback: scan PATH for common browser binaries
    for name in BROWSER_NAMES:
        path = shutil.which(name)
        if path:
            return name

    return None


def open_system_browser(url: str) -> bool:
    """Open the given URL in the default system browser.

    Returns True if successful, False otherwise.
    """
    try:
        opened = webbrowser.open(url, new=2, autoraise=True)
        if opened:
            logger.info("Opened browser: %s", url)
        else:
            logger.warning("webbrowser.open returned False for: %s", url)
        return opened
    except Exception as exc:
        logger.warning("Failed to open browser: %s", exc)
        return False


def build_dashboard_url(
    port: int = 8000,
    path: str = "/",
    token: Optional[str] = None,
    device_id: Optional[str] = None,
    tab: Optional[str] = None,
    target_id: Optional[int] = None,
    onboarding: bool = False,
) -> str:
    """Build a dashboard URL with optional auth and context params."""
    url = f"http://127.0.0.1:{port}{path}"
    params = {}
    if token:
        params["token"] = token
    if device_id:
        params["device_id"] = device_id
    if tab:
        params["tab"] = tab
    if target_id is not None:
        params["target_id"] = str(target_id)
    if onboarding:
        params["onboarding"] = "1"
    if params:
        qs = urllib.parse.urlencode(params)
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{qs}"
    return url


def open_dashboard(
    port: int = 8000,
    path: str = "/",
    token: Optional[str] = None,
    device_id: Optional[str] = None,
    tab: Optional[str] = None,
    target_id: Optional[int] = None,
    onboarding: bool = False,
) -> bool:
    """Open the dashboard with optional auth/session context."""
    url = build_dashboard_url(
        port=port,
        path=path,
        token=token,
        device_id=device_id,
        tab=tab,
        target_id=target_id,
        onboarding=onboarding,
    )
    return open_system_browser(url)


def browser_info() -> str:
    """Return a human-readable string about the detected browser."""
    name = detect_default_browser()
    if name:
        return f"Default browser: {name}"
    return "Default browser: unknown"
