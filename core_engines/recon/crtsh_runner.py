import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger("rastro.recon.crtsh")


class CrtshRunner:
    def __init__(self, output_dir: Path, timeout: int = 60):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    async def run_crtsh(self, domain: str, out_file: str = "crtsh.json") -> Path:
        import aiohttp
        path = self.output_dir / out_file
        url = f"https://crt.sh/?q=%25.{domain}&output=json"
        try:
            async with aiohttp.ClientSession() as session, session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as resp:
                    if resp.status != 200:
                        path.write_text(json.dumps({"error": f"HTTP {resp.status}"}))
                        return path
                    data = await resp.json()
                    subdomains = set()
                    for entry in data:
                        name = entry.get("name_value", "")
                        for n in name.split("\n"):
                            n = n.strip().lower()
                            if n.endswith(domain) and n not in (domain, f"*.{domain}"):
                                subdomains.add(n)
                    result = sorted(subdomains)
                    path.write_text("\n".join(result) if result else "NO RESULTS")
                    logger.info("crt.sh: %d subdomains for %s", len(result), domain)
                    return path
        except asyncio.TimeoutError:
            path.write_text("CRTSH TIMED OUT")
            return path
        except Exception as e:
            path.write_text(f"CRTSH ERROR: {e}")
            logger.warning("crt.sh failed for %s: %s", domain, e)
            return path
