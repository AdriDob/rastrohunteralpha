from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("rastro.target_auth.login")


class TargetLoginService:
    """Handles authentication against target systems.

    Supports multiple auth types:
    - bearer_token: direct token, no login needed
    - api_key: sent as header, no login needed
    - cookie: direct cookie string, no login needed
    - login_form: POST to login_url, extract session from response
    - basic_auth: HTTP Basic Authentication
    - none: no authentication
    """

    def login(
        self,
        auth_type: str,
        credentials: dict[str, Any],
    ) -> dict[str, Any]:
        """Attempt to authenticate and return session data.

        Returns:
            {
                "token": str | None,
                "cookies": dict | None,
                "expires_at": float | None,  # unix timestamp
                "error": str | None,
            }
        """
        handler = self._get_handler(auth_type)
        if handler is None:
            return {"token": None, "cookies": None, "expires_at": None, "error": f"Unsupported auth type: {auth_type}"}
        try:
            return handler(credentials)
        except Exception as exc:
            logger.warning("Login failed for auth_type=%s: %s", auth_type, exc)
            return {"token": None, "cookies": None, "expires_at": None, "error": str(exc)}

    def _get_handler(self, auth_type: str):
        handlers = {
            "bearer_token": self._handle_bearer_token,
            "api_key": self._handle_api_key,
            "cookie": self._handle_cookie,
            "login_form": self._handle_login_form,
            "basic_auth": self._handle_basic_auth,
            "none": self._handle_none,
        }
        return handlers.get(auth_type)

    @staticmethod
    def _handle_bearer_token(creds: dict) -> dict:
        token = creds.get("token", "")
        if not token:
            return {"token": None, "cookies": None, "expires_at": None, "error": "No token provided"}
        return {"token": token, "cookies": None, "expires_at": None, "error": None}

    @staticmethod
    def _handle_api_key(creds: dict) -> dict:
        api_key = creds.get("api_key", "")
        if not api_key:
            return {"token": None, "cookies": None, "expires_at": None, "error": "No API key provided"}
        # API keys are sent as headers at request time, not as login tokens
        return {"token": api_key, "cookies": None, "expires_at": None, "error": None}

    @staticmethod
    def _handle_cookie(creds: dict) -> dict:
        cookies_raw = creds.get("cookies")
        if not cookies_raw:
            return {"token": None, "cookies": None, "expires_at": None, "error": "No cookies provided"}
        if isinstance(cookies_raw, str):
            try:
                cookies_raw = json.loads(cookies_raw)
            except json.JSONDecodeError:
                pass
        if isinstance(cookies_raw, dict):
            return {"token": None, "cookies": cookies_raw, "expires_at": None, "error": None}
        return {"token": None, "cookies": None, "expires_at": None, "error": "Invalid cookie format"}

    @staticmethod
    def _handle_none(creds: dict) -> dict:
        return {"token": None, "cookies": None, "expires_at": None, "error": None}

    @staticmethod
    def _handle_login_form(creds: dict) -> dict:
        """Authenticate via HTML form POST.

        Expects credentials:
            login_url: str
            username: str
            password: str
            login_params: dict (optional, extra form fields)
        """
        import requests

        login_url = creds.get("login_url", "")
        username = creds.get("username", "")
        password = creds.get("password", "")

        if not login_url:
            return {"token": None, "cookies": None, "expires_at": None, "error": "No login_url provided"}
        if not username or not password:
            return {"token": None, "cookies": None, "expires_at": None, "error": "Username and password required for form login"}

        extra_params = creds.get("login_params", {}) or {}
        form_data = {
            "username": username,
            "password": password,
            **({k: v for k, v in extra_params.items() if isinstance(v, str)}),
        }

        resp = requests.post(
            login_url,
            data=form_data,
            timeout=30,
            allow_redirects=True,
        )

        if resp.status_code >= 400:
            return {
                "token": None,
                "cookies": None,
                "expires_at": None,
                "error": f"Login failed: HTTP {resp.status_code}",
            }

        # Extract cookies from session
        cookies = {}
        for cookie in resp.cookies:
            cookies[cookie.name] = cookie.value

        # Try to extract Bearer token from response body (common patterns)
        token = None
        try:
            body = resp.json()
            if isinstance(body, dict):
                token = (
                    body.get("access_token")
                    or body.get("token")
                    or body.get("accessToken")
                    or body.get("jwt")
                    or body.get("id_token")
                )
        except Exception:
            pass

        # Try Authorization header
        if not token:
            auth_header = resp.request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]

        # Estimate expiry from cookie
        expires_at = None
        for cookie in resp.cookies:
            if cookie.expires:
                expires_at = max(expires_at or 0, cookie.expires)

        return {
            "token": token,
            "cookies": cookies if cookies else None,
            "expires_at": expires_at,
            "error": None,
        }

    @staticmethod
    def _handle_basic_auth(creds: dict) -> dict:
        import base64
        username = creds.get("username", "")
        password = creds.get("password", "")
        if not username and not password:
            return {"token": None, "cookies": None, "expires_at": None, "error": "Basic auth requires username or password"}
        raw = f"{username}:{password}"
        encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        return {"token": f"Basic {encoded}", "cookies": None, "expires_at": None, "error": None}
