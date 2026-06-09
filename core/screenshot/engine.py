"""
screenshot.engine — Screenshot Engine.

Captura automática de endpoints críticos para evidencia visual.
Snapshots versionados por target para comparación temporal.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

LOG = logging.getLogger("rastro.screenshot")

SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "screenshots")


@dataclass
class ScreenshotResult:
    target_id: int
    endpoint_path: str
    file_path: str
    hash: str
    timestamp: str
    status_code: Optional[int] = None
    content_type: str = ""
    success: bool = False
    error: Optional[str] = None


class ScreenshotEngine:
    """Captura y versiona screenshots de endpoints."""

    def __init__(self, output_dir: str = SCREENSHOT_DIR):
        self._output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def capture(
        self,
        target_id: int,
        endpoint_path: str,
        html_content: Optional[str] = None,
        status_code: Optional[int] = None,
        content_type: str = "",
    ) -> ScreenshotResult:
        """
        Captura el contenido HTML de un endpoint y lo persiste como snapshot.

        En un entorno real usaría Playwright/Puppeteer; aquí guardamos
        el HTML directamente como evidencia textual versionada.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_path = endpoint_path.replace("/", "_").replace("?", "_").replace("=", "_")[:100]
        filename = f"target_{target_id}_{safe_path}_{ts}.html"
        filepath = os.path.join(self._output_dir, filename)

        content_hash = ""
        error = None
        success = False

        try:
            if html_content:
                content_hash = hashlib.sha256(html_content.encode()).hexdigest()[:16]
                # Guardar snapshot
                with open(filepath, "w") as f:
                    f.write(html_content)
                LOG.info("Snapshot guardado: %s (%d bytes)", filepath, len(html_content))
                success = True
            else:
                error = "No content to capture"
                # Snapshot vacío como placeholder para metadatos
                with open(filepath, "w") as f:
                    f.write(f"<!-- Empty capture for {endpoint_path} at {ts} -->")
        except IOError as e:
            error = str(e)
            LOG.error("Error guardando snapshot %s: %s", filepath, error)

        return ScreenshotResult(
            target_id=target_id,
            endpoint_path=endpoint_path,
            file_path=filepath,
            hash=content_hash,
            timestamp=ts,
            status_code=status_code,
            content_type=content_type,
            success=success,
            error=error,
        )

    def list_snapshots(self, target_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Lista snapshots disponibles, opcionalmente filtrados por target."""
        if not os.path.isdir(self._output_dir):
            return []

        snapshots = []
        for fname in os.listdir(self._output_dir):
            if not fname.endswith(".html"):
                continue
            fpath = os.path.join(self._output_dir, fname)
            stats = os.stat(fpath)
            entry = {
                "filename": fname,
                "filepath": fpath,
                "size": stats.st_size,
                "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            }
            # Extraer target_id del filename: target_{id}_...
            if fname.startswith("target_"):
                parts = fname.split("_")
                if len(parts) > 1 and parts[1].isdigit():
                    entry["target_id"] = int(parts[1])
            if target_id is None or entry.get("target_id") == target_id:
                snapshots.append(entry)

        return sorted(snapshots, key=lambda s: s["modified"], reverse=True)

    def get_diff(self, snapshot_a: str, snapshot_b: str) -> Optional[str]:
        """Compara dos snapshots y retorna las diferencias."""
        try:
            with open(snapshot_a) as f:
                content_a = f.read()
            with open(snapshot_b) as f:
                content_b = f.read()

            if content_a == content_b:
                return "Snapshots idénticos — sin cambios detectados."

            # Diff simple por líneas
            lines_a = content_a.splitlines()
            lines_b = content_b.splitlines()
            added = len(lines_b) - len(lines_a)
            changed = sum(1 for i in range(min(len(lines_a), len(lines_b))) if lines_a[i] != lines_b[i])

            return (
                f"Diferencias detectadas:\n"
                f"  - Líneas añadidas: {max(added, 0)}\n"
                f"  - Líneas eliminadas: {abs(min(added, 0))}\n"
                f"  - Líneas modificadas: {changed}"
            )
        except (IOError, FileNotFoundError) as e:
            return f"Error leyendo snapshots: {e}"
