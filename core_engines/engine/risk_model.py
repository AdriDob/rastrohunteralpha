import re
from dataclasses import dataclass, field
from typing import Any

UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
HEX_PATTERN = re.compile(r"^[0-9a-fA-F]{24}$")
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,}$")

STATIC_EXTENSIONS: set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".css", ".js", ".map",
    ".ico", ".mp4", ".webm", ".mp3", ".wav",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".zip", ".tar", ".gz",
}

LOW_VALUE_FRAGMENTS: set[str] = {
    "/health", "/status", "/metrics", "/favicon.ico",
    "/robots.txt", "/sitemap.xml", "/ping", "/version",
    "/swagger-resources", "/v2/api-docs", "/webjars",
    "/actuator", "/heartbeat", "/ready", "/live",
}

SIGNAL_LABELS: set[str] = {
    "graphql", "admin", "export", "auth", "multi_tenant",
    "billing", "identity", "internal", "file_operation",
    "import", "id_parameter", "uuid_identifier",
    "numeric_identifier", "mutation", "sensitive",
}

SIGNAL_KEYWORDS: set[str] = {
    "graphql", "admin", "export", "auth", "multi_tenant",
    "billing", "identity", "internal", "file_operation",
    "import", "uuid", "auth_smell", "idor_params",
    "ownership_risk", "sensitive_operation", "high_value_keyword",
    "object_reference_param", "api_path", "mutating_method",
}

BOLA_INDICATORS: set[str] = {
    "idor_candidate", "ownership_boundary", "tenant_boundary",
    "data_exfiltration",
}

IDOR_CONFIRMATION_SIGNALS: set[str] = {
    "uuid", "numeric_id", "idor_params", "auth_smell",
    "ownership_risk", "object_reference_param",
}

AUTH_BOUNDARY_INDICATORS: set[str] = {
    "authentication_surface", "admin_surface", "internal_surface",
}

MULTI_TENANT_ZONE_INDICATORS: set[str] = {
    "multi_tenant", "tenant_boundary",
}


@dataclass
class NoiseReport:
    discarded: list[dict[str, Any]]
    merged: list[dict[str, Any]]
    duplicates_removed: list[dict[str, Any]]
    clean: list[dict[str, Any]]
    noise_ratio: float
    reasoning: dict[str, list[str]]


@dataclass
class RiskVerdict:
    is_high_value: bool
    is_idor: bool
    is_noise: bool
    idor_confidence: float
    reason: str
    cluster_type: str | None = None


@dataclass
class AttackSurfaceMap:
    idor_clusters: list[dict[str, Any]]
    auth_boundaries: list[dict[str, Any]]
    multi_tenant_zones: list[dict[str, Any]]
    graphql_surfaces: list[dict[str, Any]]
    technologies: list[dict[str, Any]] = field(default_factory=list)
    discovered_paths: list[str] = field(default_factory=list)


@dataclass
class ROIScore:
    value_score: float
    effort_score: float
    payout_potential: float
    overall: float
    reasoning: str


@dataclass
class RiskModelConfig:
    min_risk_score: float = 15.0
    remove_static_assets: bool = True
    remove_low_value_paths: bool = True
    deduplicate_by_pattern: bool = True
    remove_no_signal: bool = True
    idor_confidence_threshold: float = 0.5
    high_value_threshold: float = 60.0
    keep_all_methods_on_dedup: bool = True


class NoiseReductionLayer:
    """
    Noise Reduction Layer — the "machine of noise reduction".

    Decides what gets ignored, what gets grouped, and what
    gets shown to the user.
    """

    def __init__(self, config: RiskModelConfig | None = None):
        self.config = config or RiskModelConfig()

    def reduce(self, endpoints: list[dict[str, Any]]) -> NoiseReport:
        if not endpoints:
            return NoiseReport(
                discarded=[], merged=[], duplicates_removed=[],
                clean=[], noise_ratio=0.0, reasoning={},
            )

        working: list[dict[str, Any]] = list(endpoints)
        discarded: list[dict[str, Any]] = []
        reasoning: dict[str, list[str]] = {}

        if self.config.remove_static_assets:
            working, removed, reasons = self._filter_static_assets(working)
            discarded.extend(removed)
            reasoning["static_assets"] = reasons

        if self.config.remove_low_value_paths:
            working, removed, reasons = self._filter_low_value(working)
            discarded.extend(removed)
            reasoning["low_value_paths"] = reasons

        if self.config.deduplicate_by_pattern:
            working, dupes, reasons = self._filter_duplicates(working)
            discarded.extend(dupes)
            reasoning["duplicates"] = reasons

        working, below, reasons = self._filter_below_threshold(working)
        discarded.extend(below)
        reasoning["below_threshold"] = reasons

        if self.config.remove_no_signal:
            working, no_sig, reasons = self._filter_no_signal(working)
            discarded.extend(no_sig)
            reasoning["no_signal"] = reasons

        total = len(endpoints)
        noise_ratio = round(len(discarded) / total, 4) if total else 0.0

        return NoiseReport(
            discarded=discarded,
            merged=[],
            duplicates_removed=[d for d in discarded if any(
                r.startswith("[duplicate]") for r in reasoning.get("duplicates", [])
            )],
            clean=working,
            noise_ratio=noise_ratio,
            reasoning=reasoning,
        )

    def _filter_static_assets(
        self, endpoints: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
        clean: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        reasons: list[str] = []

        for ep in endpoints:
            path = str(ep.get("path", ""))
            signals = ep.get("signals", [])

            if "static_asset" in signals or "low_value" in signals:
                removed.append(ep)
                reasons.append(f"[static_asset] {path} -> signal match")
                continue

            lower = path.lower()
            if any(lower.endswith(ext) for ext in STATIC_EXTENSIONS):
                removed.append(ep)
                reasons.append(f"[static_asset] {path} -> extension match")
                continue

            clean.append(ep)

        return clean, removed, reasons

    def _filter_low_value(
        self, endpoints: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
        clean: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        reasons: list[str] = []

        for ep in endpoints:
            path = str(ep.get("path", ""))
            lower = path.lower()

            matched = [f for f in LOW_VALUE_FRAGMENTS if f in lower]
            if matched:
                removed.append(ep)
                reasons.append(f"[low_value] {path} -> {matched[0]}")
                continue

            clean.append(ep)

        return clean, removed, reasons

    @staticmethod
    def _normalize_for_dedup(path: str) -> str:
        lower = path.lower().split("?", 1)[0]
        lower = re.sub(r"/+", "/", lower)
        parts = [s for s in lower.split("/") if s]
        normalized: list[str] = []
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
        self, endpoints: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
        if len(endpoints) < 2:
            return endpoints, [], []

        groups: dict[str, list[dict[str, Any]]] = {}
        for ep in endpoints:
            pattern = self._normalize_for_dedup(str(ep.get("path", "")))
            if self.config.keep_all_methods_on_dedup:
                key = f"{pattern}:::{str(ep.get('method', 'GET')).upper()}"
            else:
                key = pattern
            groups.setdefault(key, []).append(ep)

        clean: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        reasons: list[str] = []

        for _, group in groups.items():
            if len(group) == 1:
                clean.extend(group)
                continue

            group_sorted = sorted(
                group,
                key=lambda x: float(x.get("risk_score", 0)),
                reverse=True,
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

    def _filter_below_threshold(
        self, endpoints: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
        threshold = self.config.min_risk_score
        clean: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        reasons: list[str] = []

        for ep in endpoints:
            rs = float(ep.get("risk_score", 0))
            if rs < threshold:
                removed.append(ep)
                reasons.append(
                    f"[below_threshold] {ep.get('path')} "
                    f"risk_score {rs} < {threshold}"
                )
            else:
                clean.append(ep)

        return clean, removed, reasons

    def _filter_no_signal(
        self, endpoints: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
        clean: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        reasons: list[str] = []

        for ep in endpoints:
            labels = ep.get("labels", [])
            signals = ep.get("signals", [])
            risk_score = float(ep.get("risk_score", 0))
            has_idor = ep.get("potential_idor", False)

            has_signal = (
                any(ls in SIGNAL_LABELS for ls in labels)
                or any(s in SIGNAL_KEYWORDS for s in signals)
                or has_idor
            )

            if has_signal:
                clean.append(ep)
            else:
                removed.append(ep)
                reasons.append(
                    f"[no_signal] {ep.get('path')} "
                    f"risk_score {risk_score} no security signals"
                )

        return clean, removed, reasons


class RiskClassifier:
    """
    Classifies individual endpoints into risk categories.

    Decides:
      - What is "high value"
      - What is "BOLA/IDOR real"
      - What is "noise"
    """

    def __init__(self, config: RiskModelConfig | None = None):
        self.config = config or RiskModelConfig()

    def classify(self, endpoint: dict[str, Any]) -> RiskVerdict:
        path = str(endpoint.get("path", ""))
        signals = endpoint.get("signals", [])
        attack_surface = endpoint.get("attack_surface", [])
        labels = endpoint.get("labels", [])
        risk_score = float(endpoint.get("risk_score", 0))
        potential_idor = endpoint.get("potential_idor", False)

        is_noise = self._is_noise(endpoint)

        if is_noise:
            return RiskVerdict(
                is_high_value=False,
                is_idor=False,
                is_noise=True,
                idor_confidence=0.0,
                reason="Descartado por ruido: sin señales de seguridad relevantes.",
            )

        idor_confidence = self._compute_idor_confidence(
            path, signals, attack_surface, labels, risk_score, potential_idor,
        )

        is_idor = idor_confidence >= self.config.idor_confidence_threshold
        is_high_value = risk_score >= self.config.high_value_threshold or is_idor

        cluster_type = self._detect_cluster_type(attack_surface, labels)

        reasons = []
        if is_idor:
            reasons.append(f"IDOR/BOLA real con confianza {idor_confidence:.2f}")
        if is_high_value:
            reasons.append(f"Alto valor (score {risk_score})")
        if cluster_type:
            reasons.append(f"Cluster: {cluster_type}")

        return RiskVerdict(
            is_high_value=is_high_value,
            is_idor=is_idor,
            is_noise=False,
            idor_confidence=idor_confidence,
            reason=" | ".join(reasons) if reasons else "Riesgo potencial",
            cluster_type=cluster_type,
        )

    def _is_noise(self, endpoint: dict[str, Any]) -> bool:
        risk_score = float(endpoint.get("risk_score", 0))
        signals = endpoint.get("signals", [])
        labels = endpoint.get("labels", [])
        potential_idor = endpoint.get("potential_idor", False)

        if risk_score <= 5.0:
            return True

        has_signal = (
            potential_idor
            or any(s in SIGNAL_KEYWORDS for s in signals)
            or any(ls in SIGNAL_LABELS for ls in labels)
        )
        return not has_signal

    def _compute_idor_confidence(
        self,
        path: str,
        signals: list[str],
        attack_surface: list[str],
        labels: list[str],
        risk_score: float,
        potential_idor: bool,
    ) -> float:
        if not potential_idor:
            return 0.0

        confidence = 0.0
        lower = path.lower()

        has_bola_surface = any(s in BOLA_INDICATORS for s in attack_surface)
        has_idor_signals = any(s in IDOR_CONFIRMATION_SIGNALS for s in signals)

        if has_bola_surface:
            confidence += 0.3
        if has_idor_signals:
            confidence += 0.25
        if bool(UUID_PATTERN.search(path)):
            confidence += 0.15
        if any(kw in lower for kw in ["user", "account", "order", "file", "device"]):
            confidence += 0.1
        if "id_parameter" in labels:
            confidence += 0.1
        if any(
            token in lower
            for token in ["user_id", "account_id", "order_id", "file_id", "device_id"]
        ):
            confidence += 0.1

        confidence = min(confidence, 1.0)

        if risk_score >= 80:
            confidence = min(confidence + 0.1, 1.0)
        elif risk_score < 30:
            confidence = max(confidence - 0.2, 0.0)

        return round(confidence, 2)

    def _detect_cluster_type(
        self, attack_surface: list[str], labels: list[str],
    ) -> str | None:
        if any(s in BOLA_INDICATORS for s in attack_surface):
            return "IDOR"
        if any(s in AUTH_BOUNDARY_INDICATORS for s in attack_surface):
            return "Auth Boundary"
        if any(s in MULTI_TENANT_ZONE_INDICATORS for s in attack_surface):
            return "Multi-tenant Zone"
        if "graphql" in labels:
            return "GraphQL"
        return None


class AttackSurfaceMapper:
    """
    Builds the Attack Surface Map.

    Groups endpoints into:
      - IDOR clusters
      - Auth boundaries
      - Multi-tenant zones
    """

    def map(
        self,
        endpoints: list[dict[str, Any]],
        technologies: list[dict[str, Any]] | None = None,
        discovered_paths: list[str] | None = None,
    ) -> AttackSurfaceMap:
        idor_clusters: list[dict[str, Any]] = []
        auth_boundaries: list[dict[str, Any]] = []
        multi_tenant_zones: list[dict[str, Any]] = []
        graphql_surfaces: list[dict[str, Any]] = []

        for ep in endpoints:
            attack_surface = ep.get("attack_surface", [])
            labels = ep.get("labels", [])
            ep.get("signals", [])

            has_idor = any(s in BOLA_INDICATORS for s in attack_surface)
            has_auth = any(s in AUTH_BOUNDARY_INDICATORS for s in attack_surface)
            has_tenant = any(s in MULTI_TENANT_ZONE_INDICATORS for s in attack_surface)
            is_graphql = "graphql" in labels

            if has_idor:
                idor_clusters.append(ep)
            if has_auth:
                auth_boundaries.append(ep)
            if has_tenant:
                multi_tenant_zones.append(ep)
            if is_graphql:
                graphql_surfaces.append(ep)

        return AttackSurfaceMap(
            idor_clusters=idor_clusters,
            auth_boundaries=auth_boundaries,
            multi_tenant_zones=multi_tenant_zones,
            graphql_surfaces=graphql_surfaces,
            technologies=technologies or [],
            discovered_paths=discovered_paths or [],
        )


class ROIEstimator:
    """
    ROI scoring — what's worth attacking, what's not.

    Considers:
      - Vulnerability type (IDOR > XSS > Info)
      - Data sensitivity
      - Exploit complexity
      - Payout potential
    """

    VULN_PAYOUT_MULTIPLIERS = {
        "IDOR": 1.0,
        "Privilege escalation": 0.9,
        "Auth bypass": 0.85,
        "Data exposure": 0.7,
        "GraphQL logic": 0.75,
        "Business logic": 0.5,
    }

    def estimate(self, endpoint: dict[str, Any]) -> ROIScore:
        risk_score = float(endpoint.get("risk_score", 0))
        vector = endpoint.get("vector", "Business logic")
        signals = endpoint.get("signals", [])
        attack_surface = endpoint.get("attack_surface", [])
        potential_idor = endpoint.get("potential_idor", False)

        multiplier = self.VULN_PAYOUT_MULTIPLIERS.get(vector, 0.3)

        data_sensitivity = 0.0
        if any(s in BOLA_INDICATORS for s in attack_surface):
            data_sensitivity += 0.3
        if potential_idor:
            data_sensitivity += 0.2
        if "export" in signals or "data_exfiltration" in attack_surface:
            data_sensitivity += 0.2
        if "billing" in signals:
            data_sensitivity += 0.2
        if "admin" in signals:
            data_sensitivity += 0.1

        exploit_complexity = max(0.0, 1.0 - (risk_score / 100.0))

        value_score = (risk_score / 100.0) * 10.0
        effort_score = exploit_complexity * 10.0
        payout_potential = min(value_score * multiplier + data_sensitivity * 5.0, 10.0)
        overall = min(
            (payout_potential * 0.5) + (value_score * 0.3) - (effort_score * 0.2),
            10.0,
        )

        reasons = []
        if potential_idor:
            reasons.append("IDOR/BOLA potencial — alto payout")
        if data_sensitivity > 0.5:
            reasons.append("Datos sensibles detectados")
        if multiplier >= 0.8:
            reasons.append(f"Vector {vector} con buen payout histórico")

        return ROIScore(
            value_score=round(value_score, 1),
            effort_score=round(effort_score, 1),
            payout_potential=round(payout_potential, 1),
            overall=round(overall, 1),
            reasoning=" | ".join(reasons) if reasons else "ROI estándar",
        )


def analyze(
    endpoint_data: list[dict[str, Any]],
    config: RiskModelConfig | None = None,
) -> dict[str, Any]:
    """
    Full risk analysis pipeline.

    Returns a "premium" output with:
      1. Noise Reduction Layer
      2. Attack Surface Map
      3. ROI Scores per endpoint
    """
    cfg = config or RiskModelConfig()

    noise_layer = NoiseReductionLayer(cfg)
    noise_report = noise_layer.reduce(endpoint_data)

    classifier = RiskClassifier(cfg)
    mapper = AttackSurfaceMapper()
    roi_estimator = ROIEstimator()

    classified = []
    for ep in noise_report.clean:
        verdict = classifier.classify(ep)
        if verdict.is_noise:
            continue
        roi = roi_estimator.estimate(ep)
        classified.append({
            **ep,
            "risk_verdict": {
                "is_high_value": verdict.is_high_value,
                "is_idor": verdict.is_idor,
                "idor_confidence": verdict.idor_confidence,
                "cluster_type": verdict.cluster_type,
                "reason": verdict.reason,
            },
            "roi": {
                "value_score": roi.value_score,
                "effort_score": roi.effort_score,
                "payout_potential": roi.payout_potential,
                "overall": roi.overall,
                "reasoning": roi.reasoning,
            },
        })

    surface_map = mapper.map(classified)

    return {
        "noise_reduction": {
            "total_input": noise_report.total_input if hasattr(noise_report, 'total_input') else len(endpoint_data),
            "discarded_count": len(noise_report.discarded),
            "clean_count": len(noise_report.clean),
            "noise_ratio": noise_report.noise_ratio,
            "reasoning": noise_report.reasoning,
            "discarded": [
                {
                    "path": d.get("path", ""),
                    "method": d.get("method", "GET"),
                    "reason": d.get("reason", ""),
                    "risk_score": d.get("risk_score", 0),
                }
                for d in noise_report.discarded
            ],
        },
        "attack_surface_map": {
            "idor_clusters": [
                {"path": e.get("path"), "method": e.get("method"),
                 "risk_score": e.get("risk_score"), "signals": e.get("signals")}
                for e in surface_map.idor_clusters
            ],
            "auth_boundaries": [
                {"path": e.get("path"), "method": e.get("method"),
                 "risk_score": e.get("risk_score")}
                for e in surface_map.auth_boundaries
            ],
            "multi_tenant_zones": [
                {"path": e.get("path"), "method": e.get("method"),
                 "risk_score": e.get("risk_score")}
                for e in surface_map.multi_tenant_zones
            ],
            "graphql_surfaces": [
                {"path": e.get("path"), "method": e.get("method"),
                 "risk_score": e.get("risk_score")}
                for e in surface_map.graphql_surfaces
            ],
        },
        "high_value_endpoints": [
            e for e in classified if e.get("risk_verdict", {}).get("is_high_value")
        ],
        "idor_candidates": [
            e for e in classified if e.get("risk_verdict", {}).get("is_idor")
        ],
        "endpoints": classified,
    }
