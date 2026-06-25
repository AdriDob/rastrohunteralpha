import asyncio
import logging
import shutil
from pathlib import Path

logger = logging.getLogger("rastro.recon.whois")


class WhoisRunner:
    def __init__(self, output_dir: Path, timeout: int = 30):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self._binary = shutil.which("whois")

    async def run_whois(self, domain: str, out_file: str = "whois.txt") -> Path:
        path = self.output_dir / out_file
        if not self._binary:
            path.write_text("WHOIS NOT AVAILABLE")
            return path
        cmd = [self._binary, domain]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                path.write_text("WHOIS TIMED OUT")
                return path
            if stderr:
                path.write_text(stderr.decode(errors="ignore") + "\n" + stdout.decode(errors="ignore"))
            else:
                path.write_bytes(stdout or b"")
            return path
        except Exception as e:
            path.write_text(f"WHOIS ERROR: {e}")
            return path
