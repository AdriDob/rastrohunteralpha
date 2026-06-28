import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from .tools import _resolve_tool

LOG = logging.getLogger("rastro.recon.ffuf")


class FfufRunner:
    """Runs ffuf for directory/file fuzzing with predefined profiles."""

    PROFILES: dict[str, dict[str, Any]] = {
        "fast": {
            "description": "Quick scan for common admin panels and backups",
            "wordlist": "discovery/Web-Content/common.txt",
            "extensions": [],
            "max_time": 60,
        },
        "balanced": {
            "description": "Standard recon scan with common extensions",
            "wordlist": "discovery/Web-Content/raft-large-directories.txt",
            "extensions": ["php", "asp", "aspx", "jsp", "txt", "bak", "zip", "tar.gz"],
            "max_time": 180,
        },
        "deep": {
            "description": "Exhaustive fuzzing across many wordlists",
            "wordlist": "discovery/Web-Content/raft-large-files.txt",
            "extensions": [
                "php", "asp", "aspx", "jsp", "do", "action",
                "txt", "bak", "zip", "tar.gz", "sql", "xml",
                "json", "config", "conf", "log", "git", "svn",
            ],
            "max_time": 600,
        },
        "api": {
            "description": "API endpoint discovery",
            "wordlist": "discovery/Web-Content/api/actions-lowercase.txt",
            "extensions": ["json", "xml", "yaml", "yml", "proto"],
            "max_time": 300,
        },
        "subdomains": {
            "description": "Subdomain fuzzing using common names",
            "wordlist": "discovery/DNS/subdomains-top1million-5000.txt",
            "extensions": [],
            "max_time": 120,
        },
    }

    def __init__(
        self,
        output_dir: Path,
        seclists_dir: str | None = None,
        timeout: int = 300,
    ):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self._binary = _resolve_tool("ffuf") or "ffuf"
        self.seclists_dir = (
            seclists_dir
            or os.environ.get("SECLISTS_PATH")
            or "/usr/share/seclists"
        )

    def _resolve_wordlist(self, profile: str) -> str | None:
        """Resolve wordlist path for a profile."""
        if profile not in self.PROFILES:
            LOG.warning("Unknown ffuf profile '%s'", profile)
            return None
        rel_path = self.PROFILES[profile]["wordlist"]
        candidate = Path(self.seclists_dir) / rel_path
        if candidate.exists():
            return str(candidate)
        LOG.warning("Wordlist not found at %s", candidate)
        return None

    async def run_ffuf(
        self,
        target_url: str,
        profile: str = "fast",
        out_file: str | None = None,
        wordlist: str | None = None,
        extensions: list[str] | None = None,
        extra_args: list[str] | None = None,
        max_time: int | None = None,
    ) -> Path:
        """Run ffuf against a URL using a named profile or custom settings."""
        if profile and profile not in self.PROFILES:
            raise ValueError(f"Unknown ffuf profile: {profile}. Options: {list(self.PROFILES.keys())}")

        profile_cfg = self.PROFILES.get(profile, {})
        out_file = out_file or f"ffuf_{profile}_{Path(target_url).host}.txt"
        path = self.output_dir / out_file

        wordlist_path = wordlist or self._resolve_wordlist(profile)
        if not wordlist_path:
            raise FileNotFoundError(
                f"No wordlist available for profile '{profile}'. "
                f"Set SECLISTS_PATH or provide explicit wordlist."
            )

        cmd = [
            self._binary,
            "-u", target_url + "/FUZZ",
            "-w", wordlist_path,
            "-of", "json",
            "-o", str(path.with_suffix(".json")),
            "-s",  # silent
        ]

        ext_list = extensions or profile_cfg.get("extensions", [])
        for ext in ext_list:
            cmd.extend(["-e", f".{ext}"])

        if extra_args:
            cmd.extend(extra_args)

        effective_timeout = (
            min(max_time, self.timeout)
            if max_time
            else profile_cfg.get("max_time", self.timeout)
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=effective_timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            path.write_text("FFUF TIMED OUT")
            return path

        if stderr:
            err_text = stderr.decode(errors="ignore")
            if "error" in err_text.lower() or "fatal" in err_text.lower():
                LOG.warning("ffuf error for %s: %s", target_url, err_text[:300])

        return path

    def parse_results(self, json_path: Path) -> list[dict[str, Any]]:
        """Parse ffuf JSON output into structured results."""
        if not json_path.exists():
            return []
        try:
            data = json.loads(json_path.read_text())
            results = data.get("results", []) if isinstance(data, dict) else data
            parsed = []
            for r in results:
                parsed.append({
                    "url": r.get("url", ""),
                    "status": r.get("status", 0),
                    "length": r.get("length", 0),
                    "words": r.get("words", 0),
                    "lines": r.get("lines", 0),
                    "content_type": r.get("content_type", ""),
                    "redirect_location": r.get("redirectlocation", ""),
                    "host": r.get("host", ""),
                    "input": r.get("input", {}),
                })
            return parsed
        except (json.JSONDecodeError, KeyError) as e:
            LOG.warning("Failed to parse ffuf JSON: %s", e)
            return []

    def categorize_findings(
        self, results: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Categorize ffuf results by response status."""
        categories: dict[str, list[dict[str, Any]]] = {
            "admin_panels": [],
            "api_endpoints": [],
            "backups": [],
            "interesting": [],
            "info": [],
            "error": [],
        }
        for r in results:
            status = r.get("status", 0)
            url = r.get("url", "")
            if status == 200:
                if any(kw in url for kw in ["admin", "login", "dashboard", "panel", "cp"]):
                    categories["admin_panels"].append(r)
                elif any(kw in url for kw in ["api", "v1", "v2", "graphql", "rest"]):
                    categories["api_endpoints"].append(r)
                elif any(url.endswith(ext) for ext in [".bak", ".zip", ".tar", ".gz", ".old", ".swp"]):
                    categories["backups"].append(r)
                else:
                    categories["interesting"].append(r)
            elif 200 < status < 400:
                categories["info"].append(r)
            else:
                categories["error"].append(r)
        return categories

    async def discover_paths(
        self, target_url: str, profile: str = "fast"
    ) -> list[dict[str, Any]]:
        """Convenience: run ffuf and parse results in one call."""
        out = await self.run_ffuf(target_url, profile=profile)
        json_path = out.with_suffix(".json") if out.suffix != ".json" else out
        return self.parse_results(json_path)
