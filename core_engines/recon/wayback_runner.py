import asyncio
from pathlib import Path


class WaybackRunner:
    def __init__(self, output_dir: Path, timeout: int = 180):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    async def run_wayback(self, domain: str, out_file: str = "wayback.txt") -> Path:
        path = self.output_dir / out_file
        cmd = ["waybackurls", domain]
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
            path.write_text("WAYBACK TIMED OUT")
            return path
        if stderr:
            path.write_text(
                stderr.decode(errors="ignore") + "\n" + stdout.decode(errors="ignore")
            )
        else:
            path.write_bytes(stdout or b"")
        return path
