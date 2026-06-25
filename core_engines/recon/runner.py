import asyncio
import json
import logging
from pathlib import Path
from typing import Iterable, Any, Coroutine

from .crtsh_runner import CrtshRunner
from .ffuf_runner import FfufRunner
from .gau_runner import GauRunner
from .httpx_runner import HttpxRunner
from .katana_runner import KatanaRunner
from .nuclei_runner import NucleiRunner
from .parser import EndpointParser
from .seclists_profiles import WORDLISTS, get_recommended_profiles, available_wordlists
from .subfinder_runner import SubfinderRunner
from .wayback_runner import WaybackRunner
from .whois_runner import WhoisRunner

logger = logging.getLogger("rastro.recon")


class ReconRunner:
    def __init__(self, target_root: Path):
        self.target_root = target_root

        self.recon_dir = self.target_root / "recon"
        self.endpoints_dir = self.target_root / "endpoints"
        self.analysis_dir = self.target_root / "analysis"
        self.logs_dir = self.target_root / "logs"
        self.screenshots_dir = self.target_root / "screenshots"

        for folder in [
            self.recon_dir,
            self.endpoints_dir,
            self.analysis_dir,
            self.logs_dir,
            self.screenshots_dir,
        ]:
            folder.mkdir(parents=True, exist_ok=True)

        self.subfinder = SubfinderRunner(self.recon_dir)
        self.httpx = HttpxRunner(self.recon_dir)
        self.katana = KatanaRunner(self.recon_dir)
        self.wayback = WaybackRunner(self.recon_dir)
        self.nuclei = NucleiRunner(self.recon_dir)
        self.gau = GauRunner(self.recon_dir)
        self.ffuf = FfufRunner(self.recon_dir)
        self.crtsh = CrtshRunner(self.recon_dir)
        self.whois = WhoisRunner(self.recon_dir)

        self.parser = EndpointParser()

    async def _safe_run_tool(
        self,
        tool_name: str,
        coroutine: Coroutine,
        timeout: int = 120,
    ) -> Any:
        try:
            logger.info(f"Starting tool: {tool_name}")

            result = await asyncio.wait_for(
                coroutine,
                timeout=timeout,
            )

            logger.info(f"Tool completed: {tool_name}")

            return result

        except asyncio.TimeoutError:
            logger.error(f"Tool timeout: {tool_name}")
            return None

        except Exception as e:
            logger.error(
                f"Tool {tool_name} failed: {str(e)}",
                exc_info=True,
            )
            return None

    async def run_pipeline(
        self,
        domain: str,
        mode: str = "FAST",
    ) -> dict[str, str]:

        domain = domain.strip()

        if not domain:
            raise ValueError("Domain is required for recon.")

        outputs: dict[str, str] = {}
        source_files = []

        logger.info(f"Starting recon pipeline for {domain} in mode {mode}")

        # SUBFINDER

        subfinder_path = await self._safe_run_tool(
            "subfinder",
            self.subfinder.run_subfinder(
                domain,
                "subfinder.txt",
            ),
            timeout=120,
        )

        if subfinder_path:
            outputs["subfinder"] = str(subfinder_path)

        # PARALLEL TASKS

        crtsh_task = asyncio.create_task(
            self._safe_run_tool(
                "crtsh",
                self.crtsh.run_crtsh(domain, "crtsh.txt"),
                timeout=60,
            )
        )

        whois_task = asyncio.create_task(
            self._safe_run_tool(
                "whois",
                self.whois.run_whois(domain, "whois.txt"),
                timeout=30,
            )
        )

        wayback_task = asyncio.create_task(
            self._safe_run_tool(
                "wayback",
                self.wayback.run_wayback(
                    domain,
                    "wayback.txt",
                ),
                timeout=180,
            )
        )

        katana_task = asyncio.create_task(
            self._safe_run_tool(
                "katana",
                self.katana.run_katana(
                    domain,
                    "katana.json",
                ),
                timeout=300,
            )
        )

        # HTTPX ONLY FOR DEEP/API

        if mode.upper() in {"DEEP", "API"}:

            httpx_input = subfinder_path if subfinder_path else domain

            httpx_path = await self._safe_run_tool(
                "httpx",
                self.httpx.run_httpx(
                    httpx_input,
                    "httpx.json",
                ),
                timeout=180,
            )

            if httpx_path:
                outputs["httpx"] = str(httpx_path)
                source_files.append(httpx_path)

        # WAIT TASKS

        wayback_path = await wayback_task

        if wayback_path:
            outputs["wayback"] = str(wayback_path)
            source_files.append(wayback_path)

        katana_path = await katana_task

        if katana_path:
            outputs["katana"] = str(katana_path)
            source_files.append(katana_path)

        # CRT.SH + WHOIS

        crtsh_path = await crtsh_task
        if crtsh_path:
            outputs["crtsh"] = str(crtsh_path)
            source_files.append(crtsh_path)

        whois_path = await whois_task
        if whois_path:
            outputs["whois"] = str(whois_path)
            source_files.append(whois_path)

        # NORMALIZATION

        normalized_path = self.endpoints_dir / "normalized_endpoints.json"

        parser_output = self.parser.parse_files(
            [p for p in source_files if p],
            normalized_path,
        )

        outputs["normalized_endpoints"] = str(parser_output)

        # LOAD NORMALIZED ENDPOINTS SAFELY

        endpoint_entries = []

        if parser_output.exists():

            try:
                with parser_output.open(
                    "r",
                    encoding="utf-8",
                    errors="ignore",
                ) as file:

                    endpoint_entries = json.load(file)

                    if not isinstance(
                        endpoint_entries,
                        list,
                    ):
                        logger.warning("normalized_endpoints.json is not a list")
                        endpoint_entries = []

            except json.JSONDecodeError as exc:
                logger.error(f"Invalid normalized endpoints JSON: {exc}")

            except Exception as exc:
                logger.error(f"Failed reading normalized endpoints: {exc}")

        logger.info(f"Normalized endpoints: {len(endpoint_entries)}")

        # NUCLEI VULNERABILITY SCAN (post-recon)

        if endpoint_entries and mode.upper() in {"DEEP", "API"}:
            targets_file = self.recon_dir / "nuclei_targets.txt"
            urls = [
                f"{ep.get('url', ep.get('path', ''))}"
                for ep in endpoint_entries
                if ep.get("url") or ep.get("path")
            ]
            if urls:
                targets_file.write_text("\n".join(urls))
                nuclei_path = await self._safe_run_tool(
                    "nuclei",
                    self.nuclei.run_nuclei(
                        targets_file,
                        "nuclei.json",
                        severity="medium,high,critical",
                    ),
                    timeout=300,
                )
                if nuclei_path:
                    outputs["nuclei"] = str(nuclei_path)
                    findings = await self.nuclei.load_findings(nuclei_path)
                    logger.info("nuclei findings: %d", len(findings))

        # SUMMARY

        summary_path = self.analysis_dir / "summary.json"

        summary_data = {
            "domain": domain,
            "mode": mode.upper(),
            "outputs": outputs,
            "endpoint_count": len(endpoint_entries),
        }

        try:
            summary_path.write_text(
                json.dumps(
                    summary_data,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            outputs["summary"] = str(summary_path)

        except Exception as exc:
            logger.error(f"Failed writing summary.json: {exc}")

        logger.info(f"Recon pipeline completed for {domain}")

        return outputs

    async def join_results(
        self,
        paths: Iterable[Path],
        out_file: str,
    ) -> Path:

        target = self.target_root / out_file

        with target.open("wb") as writer:

            for path in paths:

                if path.exists():

                    writer.write(path.read_bytes())
                    writer.write(b"\n")

        return target
