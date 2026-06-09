import asyncio
from pathlib import Path
from typing import Optional


class SubfinderRunner:
    def __init__(self, output_dir: Path, timeout: int = 120):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    async def run_subfinder(self, domain: str, out_file: str = "subfinder.txt") -> Path:
        path = self.output_dir / out_file
        cmd = ["subfinder", "-d", domain, "-silent"]
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
            path.write_text("SUBFINDER TIMED OUT")
            return path
        if stderr:
            path.write_text(
                stderr.decode(errors="ignore") + "\n" + stdout.decode(errors="ignore")
            )
        else:
            path.write_bytes(stdout or b"")
        return path

    async def load_domains(self, path: Path) -> list[str]:
        if not path.exists():
            return []
        seen = set()
        domains = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                domains.append(line)
        return domains
