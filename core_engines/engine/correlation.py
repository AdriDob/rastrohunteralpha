"""
Correlation engine: fuses findings from multiple sources
(Discovery, GAU, FFUF, Burp, ZAP, Huntr, H1, BC, Memory)
into unified threat models.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

LOG = logging.getLogger("rastro.engine.correlation")

# Source priority (higher = more authoritative)
SOURCE_PRIORITY = {
    "burp": 100,
    "zap": 90,
    "hackerone": 80,
    "bugcrowd": 75,
    "huntr": 70,
    "ffuf": 50,
    "gau": 40,
    "discovery": 30,
    "recon": 20,
    "memory": 10,
}


@dataclass
class CorrelatedFinding:
    """A finding enriched with correlation data."""
    id: str
    title: str
    description: str
    severity: str  # critical, high, medium, low, info
    source: str
    source_priority: int = 0
    url: str = ""
    host: str = ""
    risk_score: float = 0.0
    tags: list[str] = field(default_factory=list)
    cwe_ids: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)
    related_findings: list[str] = field(default_factory=list)
    created_at: str = ""


def _severity_score(severity: str) -> float:
    mapping = {"critical": 10.0, "high": 7.5, "medium": 5.0, "low": 2.5, "info": 0.0}
    return mapping.get(severity.lower(), 1.0)


class CorrelationEngine:
    """Fuses findings from multiple sources into correlated threat models."""

    def __init__(self):
        self.findings: list[CorrelatedFinding] = []
        self._dedup_cache: set[str] = set()

    def ingest(
        self,
        source: str,
        items: list[Any],
        extractor_fn=None,
    ) -> list[CorrelatedFinding]:
        """Ingest findings from a source, deduplicate, and correlate."""
        parsed = extractor_fn(items) if extractor_fn else self._default_extract(source, items)

        new_findings = []
        for item in parsed:
            dedup_key = f"{item.url}:{item.title}:{source}"
            if dedup_key in self._dedup_cache:
                continue
            self._dedup_cache.add(dedup_key)
            item.source_priority = SOURCE_PRIORITY.get(source, 0)
            self.findings.append(item)
            new_findings.append(item)

        if new_findings:
            LOG.info("Correlation: ingested %d new findings from %s", len(new_findings), source)
            self._correlate(new_findings)

        return new_findings

    def _default_extract(
        self, source: str, items: list[dict[str, Any]]
    ) -> list[CorrelatedFinding]:
        """Default extraction from dict items with common fields."""
        now = datetime.now().isoformat()
        findings = []
        for i, item in enumerate(items):
            if isinstance(item, dict):
                title = item.get("title", item.get("alert", item.get("name", f"{source}_finding_{i}")))
                findings.append(CorrelatedFinding(
                    id=f"{source}_{i}",
                    title=str(title),
                    description=item.get("description", item.get("detail", "")),
                    severity=item.get("severity", item.get("risk", "info")),
                    source=source,
                    url=item.get("url", ""),
                    host=item.get("host", ""),
                    tags=item.get("tags", []),
                    cwe_ids=item.get("cwe_ids", []),
                    raw_data=item,
                    created_at=now,
                ))
        return findings

    def _correlate(self, new_findings: list[CorrelatedFinding]) -> None:
        """Link related findings by URL host and CWE."""
        host_groups = defaultdict(list)
        cwe_groups = defaultdict(list)

        for f in self.findings:
            host = f.host or extract_host(f.url)
            if host:
                host_groups[host].append(f)
            for cwe in f.cwe_ids:
                cwe_groups[cwe].append(f)

        for f in new_findings:
            related = set()
            host = f.host or extract_host(f.url)
            if host:
                for other in host_groups.get(host, []):
                    if other.id != f.id:
                        related.add(other.id)
            for cwe in f.cwe_ids:
                for other in cwe_groups.get(cwe, []):
                    if other.id != f.id:
                        related.add(other.id)
            f.related_findings = list(related)

    def get_priority_findings(
        self, min_severity: str = "medium", top_n: int = 50
    ) -> list[CorrelatedFinding]:
        """Get top findings by priority and severity."""
        min_score = _severity_score(min_severity)
        scored = [
            f for f in self.findings
            if _severity_score(f.severity) >= min_score
        ]
        scored.sort(
            key=lambda f: (f.source_priority, _severity_score(f.severity)),
            reverse=True,
        )
        return scored[:top_n]

    def get_findings_by_host(self, host: str) -> list[CorrelatedFinding]:
        """Get all findings for a specific host."""
        return [
            f for f in self.findings
            if host in (f.host or extract_host(f.url))
        ]

    def get_source_summary(self) -> dict[str, int]:
        """Count findings per source."""
        summary: dict[str, int] = defaultdict(int)
        for f in self.findings:
            summary[f.source] += 1
        return dict(summary)

    def get_severity_summary(self) -> dict[str, int]:
        """Count findings by severity."""
        summary: dict[str, int] = defaultdict(int)
        for f in self.findings:
            summary[f.severity.lower()] += 1
        return dict(summary)

    def clear(self) -> None:
        """Reset the correlation engine."""
        self.findings.clear()
        self._dedup_cache.clear()


def extract_host(url: str) -> str:
    """Extract hostname from URL."""
    if not url:
        return ""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except Exception:
        return url


def _dedup(items: list[CorrelatedFinding], key_fn=None) -> list[CorrelatedFinding]:
    """Generic deduplication helper."""
    seen: set[str] = set()
    result = []
    for item in items:
        k = key_fn(item) if key_fn else item.url
        if k and k not in seen:
            seen.add(k)
            result.append(item)
    return result
