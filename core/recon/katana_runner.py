import asyncio
from pathlib import Path


class KatanaRunner:
    def __init__(self, output_dir: Path, timeout: int = 240):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    async def run_katana(self, domain: str, out_file: str = "katana.json") -> Path:
        path = self.output_dir / out_file
        cmd = ["katana", "-u", domain, "-jsonl", "-o", str(path)]
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
            path.write_text("KATANA TIMED OUT")
            return path
        if stderr:
            path.write_text(
                stderr.decode(errors="ignore") + "\n" + stdout.decode(errors="ignore")
            )
        return path
