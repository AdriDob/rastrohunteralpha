import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

HEX_PATTERN = re.compile(r"^[0-9a-fA-F]{24}$")

TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,}$")

STATIC_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".css", ".js", ".map",
    ".ico", ".mp4", ".webm", ".mp3", ".wav",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".zip", ".tar", ".gz",
}

LOW_VALUE_FRAGMENTS: Set[str] = {
    "/health", "/status", "/metrics", "/favicon.ico",
    "/robots.txt", "/sitemap.xml", "/ping", "/version",
    "/swagger-resources", "/v2/api-docs", "/webjars",
    "/actuator", "/heartbeat", "/ready", "/live",
}

SIGNAL_LABELS: Set[str] = {
    "graphql", "admin", "export", "auth", "multi_tenant",
    "billing", "identity", "internal", "file_operation",
    "import", "id_parameter", "uuid_identifier",
    "numeric_identifier", "mutation", "sensitive",
}

SIGNAL_KEYWORDS: Set[str] = {
    "graphql", "admin", "export", "auth", "multi_tenant",
    "billing", "identity", "internal", "file_operation",
    "import", "uuid", "auth_smell", "idor_params",
    "ownership_risk", "sensitive_operation", "high_value_keyword",
    "object_reference_param", "api_path", "mutating_method",
}


@dataclass
class NoiseConfig:
    min_risk_score: float = 15.0
    remove_static_assets: bool = True
    remove_low_value_paths: bool = True
    deduplicate_by_pattern: bool = True
    remove_no_signal: bool = True
    keep_all_methods_on_dedup: bool = True


@dataclass
class NoiseReport:
    clean_endpoints: List[Dict[str, Any]]
    noise_endpoints: List[Dict[str, Any]]
    noise_ratio: float
    total_input: int
    reasoning: Dict[str, List[str]]


class NoiseReductionEngine:
    """
    Deterministic noise reduction pipeline.

    Consumes scored endpoint dicts (from core.engine.unified_scoring + identity fields)
    and applies a sequential filter chain to separate signal from noise.

    Designed as a pre-processor for Hypothesis Engine.
    """

    def __init__(self, config: Optional[NoiseConfig] = None):
        self.config = config or NoiseConfig()

    def analyze(self, scored_endpoints: List[Dict[str, Any]]) -> NoiseReport:
        if not scored_endpoints:
            return NoiseReport(
                clean_endpoints=[],
                noise_endpoints=[],
                noise_ratio=0.0,
                total_input=0,
                reasoning={},
            )

        working: List[Dict[str, Any]] = list(scored_endpoints)
        noise: List[Dict[str, Any]] = []
        reasoning: Dict[str, List[str]] = {}

        if self.config.remove_static_assets:
            working, removed, reasons = self._filter_static_assets(working)
            noise.extend(removed)
            reasoning["static_assets"] = reasons

        if self.config.remove_low_value_paths:
            working, removed, reasons = self._filter_low_value(working)
            noise.extend(removed)
            reasoning["low_value_paths"] = reasons

        if self.config.deduplicate_by_pattern:
            working, removed, reasons = self._filter_duplicates(working)
            noise.extend(removed)
            reasoning["duplicates"] = reasons

        working, removed, reasons = self._filter_below_threshold(working)
        noise.extend(removed)
        reasoning["below_threshold"] = reasons

        if self.config.remove_no_signal:
            working, removed, reasons = self._filter_no_signal(working)
            noise.extend(removed)
            reasoning["no_signal"] = reasons

        total = len(scored_endpoints)
        noise_ratio = round(len(noise) / total, 4) if total else 0.0

        return NoiseReport(
            clean_endpoints=working,
            noise_endpoints=noise,
            noise_ratio=noise_ratio,
            total_input=total,
            reasoning=reasoning,
        )

    # ── Filter: static assets (extensions) ──────────────────────────────

    def _filter_static_assets(
        self, endpoints: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        clean: List[Dict[str, Any]] = []
        removed: List[Dict[str, Any]] = []
        reasons: List[str] = []

        for ep in endpoints:
            path = str(ep.get("path", ""))
            signals = ep.get("signals", [])

            if "static_asset" in signals:
                removed.append(ep)
                reasons.append(f"[static_asset] {path} -> signal static_asset")
                continue

            lower = path.lower()
            if any(lower.endswith(ext) for ext in STATIC_EXTENSIONS):
                removed.append(ep)
                reasons.append(f"[static_asset] {path} -> extension match")
                continue

            clean.append(ep)

        return clean, removed, reasons

    # ── Filter: low-value paths (health, status, etc.) ──────────────────

    def _filter_low_value(
        self, endpoints: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        clean: List[Dict[str, Any]] = []
        removed: List[Dict[str, Any]] = []
        reasons: List[str] = []

        for ep in endpoints:
            path = str(ep.get("path", ""))
            signals = ep.get("signals", [])
            lower = path.lower()

            if "low_value" in signals:
                removed.append(ep)
                reasons.append(f"[low_value] {path} -> signal low_value")
                continue

            matched = [f for f in LOW_VALUE_FRAGMENTS if f in lower]
            if matched:
                removed.append(ep)
                reasons.append(f"[low_value] {path} -> fragment {matched[0]}")
                continue

            clean.append(ep)

        return clean, removed, reasons

    # ── Filter: duplicates by normalized path pattern ───────────────────

    @staticmethod
    def _normalize_for_dedup(path: str) -> str:
        lower = path.lower().split("?", 1)[0]
        lower = re.sub(r"/+", "/", lower)
        parts = [s for s in lower.split("/") if s]
        normalized: List[str] = []
        for segment in parts:
            if UUID_PATTERN.search(segment):
                normalized.append("{uuid}")
            elif segment.isdigit():
                normalized.append("{id}")
            elif HEX_PATTERN.match(segment):
                normalized.append("{hex}")
            elif TOKEN_PATTERN.match(segment):
                normalized.append("{token}")
            else:
                normalized.append(segment)
        return "/" + "/".join(normalized) if normalized else "/"

    def _filter_duplicates(
        self, endpoints: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        if len(endpoints) < 2:
            return endpoints, [], []

        # Group by (normalized_pattern, method) or just pattern
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for ep in endpoints:
            pattern = self._normalize_for_dedup(str(ep.get("path", "")))
            if self.config.keep_all_methods_on_dedup:
                method = str(ep.get("method", "GET")).upper()
                key = f"{pattern}:::{method}"
            else:
                key = pattern
            groups.setdefault(key, []).append(ep)

        clean: List[Dict[str, Any]] = []
        removed: List[Dict[str, Any]] = []
        reasons: List[str] = []

        for key, group in groups.items():
            if len(group) == 1:
                clean.extend(group)
                continue

            group_sorted = sorted(
                group, key=lambda x: float(x.get("risk_score", 0)), reverse=True
            )
            kept = group_sorted[0]
            clean.append(kept)
            for ep in group_sorted[1:]:
                removed.append(ep)
                reasons.append(
                    f"[duplicate] {ep.get('path')} "
                    f"(score {ep.get('risk_score')}) "
                    f"duplicate of {kept.get('path')} "
                    f"(score {kept.get('risk_score')})"
                )

        return clean, removed, reasons

    # ── Filter: below risk score threshold ──────────────────────────────

    def _filter_below_threshold(
        self, endpoints: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        threshold = self.config.min_risk_score
        clean: List[Dict[str, Any]] = []
        removed: List[Dict[str, Any]] = []
        reasons: List[str] = []

        for ep in endpoints:
            score = float(ep.get("risk_score", 0))
            if score < threshold:
                removed.append(ep)
                reasons.append(
                    f"[below_threshold] {ep.get('path')} "
                    f"risk_score {score} < threshold {threshold}"
                )
            else:
                clean.append(ep)

        return clean, removed, reasons

    # ── Filter: no security-relevant signals ────────────────────────────

    def _filter_no_signal(
        self, endpoints: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        clean: List[Dict[str, Any]] = []
        removed: List[Dict[str, Any]] = []
        reasons: List[str] = []

        for ep in endpoints:
            labels = ep.get("labels", [])
            signals = ep.get("signals", [])
            risk_score = float(ep.get("risk_score", 0))

            has_signal_label = any(ls in SIGNAL_LABELS for ls in labels)
            has_signal_keyword = any(s in SIGNAL_KEYWORDS for s in signals)
            has_idor = ep.get("potential_idor", False)

            if has_signal_label or has_signal_keyword or has_idor:
                clean.append(ep)
            else:
                removed.append(ep)
                reasons.append(
                    f"[no_signal] {ep.get('path')} "
                    f"risk_score {risk_score} no security signals"
                )

        return clean, removed, reasons

    # ── Utility: run a single filter (for composability) ────────────────

    def filter_only(
        self, scored_endpoints: List[Dict[str, Any]], filter_name: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        registry = {
            "static_assets": self._filter_static_assets,
            "low_value": self._filter_low_value,
            "duplicates": self._filter_duplicates,
            "below_threshold": self._filter_below_threshold,
            "no_signal": self._filter_no_signal,
        }
        fn = registry.get(filter_name)
        if fn is None:
            return scored_endpoints, []
        clean, removed, _ = fn(scored_endpoints)
        return clean, removed
