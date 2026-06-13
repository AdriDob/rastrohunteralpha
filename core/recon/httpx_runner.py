import asyncio
from pathlib import Path
from typing import Optional

from .tools import _resolve_tool


class HttpxRunner:
    def __init__(self, output_dir: Path, timeout: int = 180):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self._binary = _resolve_tool("httpx") or "httpx"

    async def run_httpx(self, input_file: Path, out_file: str = "httpx.json") -> Path:
        path = self.output_dir / out_file
        cmd = [self._binary, "-l", str(input_file), "-json", "-o", str(path), "-silent"]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            path.write_text("HTTPX TIMED OUT")
            return path
        if stderr:
            path.write_text(
                stderr.decode(errors="ignore") + "\n" + stdout.decode(errors="ignore")
            )
        return path

    async def load_urls(self, path: Path) -> list[str]:
        if not path.exists():
            return []
        urls = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if line:
                urls.append(line)
        return urls
