"""Email notification adapter — sends via SMTP."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

logger = logging.getLogger("rastro.notifications.email")


class EmailAdapter:
    def __init__(self) -> None:
        self._host = os.environ.get("RASTRO_SMTP_HOST", "")
        self._port = int(os.environ.get("RASTRO_SMTP_PORT", "587"))
        self._user = os.environ.get("RASTRO_SMTP_USER", "")
        self._password = os.environ.get("RASTRO_SMTP_PASSWORD", "")
        self._from = os.environ.get("RASTRO_SMTP_FROM", "rastro@localhost")
        self._to = os.environ.get("RASTRO_NOTIFICATION_EMAIL", "")
        self._enabled = bool(self._host and self._to)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def send(self, title: str, message: str, priority: str = "medium", metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not self._enabled:
            logger.debug("Email disabled — set RASTRO_SMTP_HOST and RASTRO_NOTIFICATION_EMAIL")
            return False

        try:
            html = f"""<html><body style="font-family:sans-serif;padding:20px">
<h2 style="color:#7c3aed;">{title}</h2>
<p>{message}</p>
<hr><p style="color:#999;font-size:11px;">Rastro Notification · Priority: {priority}</p>
</body></html>"""

            msg = MIMEText(html, "html")
            msg["Subject"] = f"[Rastro] {title}"
            msg["From"] = self._from
            msg["To"] = self._to

            with smtplib.SMTP(self._host, self._port) as server:
                server.starttls()
                if self._user:
                    server.login(self._user, self._password)
                server.send_message(msg)

            logger.info("Email sent: %s → %s", title, self._to)
            return True
        except Exception as exc:
            logger.warning("Email send failed: %s", exc)
            return False


_EMAIL: Optional[EmailAdapter] = None


def get_email_adapter() -> EmailAdapter:
    global _EMAIL
    if _EMAIL is None:
        _EMAIL = EmailAdapter()
    return _EMAIL
