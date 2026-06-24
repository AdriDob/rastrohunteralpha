import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional, Set

from .tools import _resolve_tool

LOG = logging.getLogger("rastro.recon.gau")


class GauRunner:
    """Runs gau (Get All URLs) to discover historical URLs for a domain."""

    def __init__(self, output_dir: Path, timeout: int = 120):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self._binary = _resolve_tool("gau") or "gau"

    async def run_gau(
        self,
        domain: str,
        out_file: str = "gau.txt",
        max_urls: int = 5000,
        filters: Optional[List[str]] = None,
    ) -> Path:
        """Fetch historical URLs for domain using gau."""
        path = self.output_dir / out_file
        cmd = [
            self._binary,
            "--o", str(path),
            "--max-urls", str(max_urls),
            domain,
        ]
        if filters:
            cmd.extend(["--filter", ",".join(filters)])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            path.write_text("GAU TIMED OUT")
            return path

        if stdout:
            LOG.debug("gau stdout: %s", stdout.decode(errors="ignore")[:200])
        if stderr:
            err = stderr.decode(errors="ignore")
            if "error" in err.lower():
                LOG.warning("gau stderr: %s", err[:300])

        return path

    def load_urls(self, path: Path) -> List[str]:
        """Load and deduplicate URLs from a gau output file."""
        if not path.exists():
            return []
        seen: Set[str] = set()
        urls = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                urls.append(line)
        return urls

    async def discover_endpoints(self, domain: str) -> List[str]:
        """Convenience: run gau and load results in one call."""
        out = await self.run_gau(domain)
        return self.load_urls(out)
