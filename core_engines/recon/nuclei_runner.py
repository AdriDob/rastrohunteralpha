import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional

from .tools import _resolve_tool

logger = logging.getLogger("rastro.recon.nuclei")


class NucleiRunner:
    def __init__(self, output_dir: Path, timeout: int = 300):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self._binary = _resolve_tool("nuclei") or "nuclei"

    async def run_nuclei(
        self,
        input_file: Path,
        out_file: str = "nuclei.json",
        severity: str = "medium,high,critical",
        tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
    ) -> Path:
        path = self.output_dir / out_file
        cmd = [
            self._binary,
            "-l", str(input_file),
            "-jsonl",
            "-o", str(path),
            "-severity", severity,
            "-silent",
        ]
        if tags:
            cmd.extend(["-tags", ",".join(tags)])
        if exclude_tags:
            cmd.extend(["-exclude-tags", ",".join(exclude_tags)])

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
            path.write_text("NUCLEI TIMED OUT")
            return path

        if stderr:
            err_text = stderr.decode(errors="ignore")
            if "warning" not in err_text.lower():
                path.write_text(err_text + "\n" + stdout.decode(errors="ignore"))
            else:
                path.write_bytes(stdout or b"")
        else:
            path.write_bytes(stdout or b"")

        logger.info(
            "nuclei scan complete: %s (%s)",
            path,
            ", ".join(self._count_findings(path)) if path.exists() else "no output",
        )
        return path

    async def load_findings(self, path: Path) -> List[dict]:
        if not path.exists():
            return []
        findings = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("NUCLEI"):
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return findings

    def _count_findings(self, path: Path) -> List[str]:
        findings = []
        sev_counts: dict = {}
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("NUCLEI"):
                continue
            try:
                entry = json.loads(line)
                sev = entry.get("info", {}).get("severity", "unknown")
                sev_counts[sev] = sev_counts.get(sev, 0) + 1
                findings.append(entry)
            except json.JSONDecodeError:
                continue
        if not findings:
            return ["no findings"]
        return [f"severity/{sev}={count}" for sev, count in sorted(sev_counts.items())]
