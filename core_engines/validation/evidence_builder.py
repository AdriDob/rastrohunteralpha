from typing import Any

from core_engines.validation.replayer import ComparisonResult, RequestSpec


class EvidenceBuilder:
    def build_from_comparison(
        self,
        request_spec: RequestSpec,
        auth_label: str,
        comparison: ComparisonResult,
        verdict_id: int | None = None,
    ) -> dict[str, Any]:
        import json as _json

        return {
            "verdict_id": verdict_id,
            "attempt_label": f"attempt_{comparison.attempt}",
            "request_url": request_spec.url,
            "request_method": request_spec.method,
            "request_headers": _json.dumps(request_spec.headers) if request_spec.headers else None,
            "request_params": _json.dumps(request_spec.params) if request_spec.params else None,
            "request_body": request_spec.body,
            "auth_label": auth_label,
            "response_status": comparison.probe.status_code,
            "response_headers": _json.dumps(comparison.probe.headers) if comparison.probe.headers else None,
            "response_body": comparison.probe.body,
            "response_body_hash": comparison.probe.body_hash,
            "status_match": "true" if comparison.status_match else "false",
            "body_diff_ratio": str(comparison.body_diff_ratio),
            "sensitive_fields": _json.dumps(comparison.sensitive_fields_detected),
            "consistent": "true" if comparison.consistent else "false",
            "curl_command": self._build_curl(request_spec, auth_label, comparison),
        }

    def build_all_from_comparisons(
        self,
        request_spec: RequestSpec,
        auth_context: Any,
        comparisons: list[ComparisonResult],
        verdict_id: int | None = None,
    ) -> list[dict[str, Any]]:
        auth_label = getattr(auth_context, "label", "unknown")
        return [
            self.build_from_comparison(request_spec, auth_label, c, verdict_id)
            for c in comparisons
        ]

    def build_comparison_summary(
        self, comparisons: list[ComparisonResult]
    ) -> dict[str, Any]:
        if not comparisons:
            return {"total": 0}
        return {
            "total": len(comparisons),
            "consistent_count": sum(1 for c in comparisons if c.consistent),
            "has_rate_limit": any(c.has_rate_limit for c in comparisons),
            "has_timeout": any(c.has_timeout for c in comparisons),
            "body_diff_range": [
                min(c.body_diff_ratio for c in comparisons),
                max(c.body_diff_ratio for c in comparisons),
            ],
            "status_matches": sum(1 for c in comparisons if c.status_match),
            "sensitive_fields_found": sorted(set(
                f for c in comparisons for f in c.sensitive_fields_detected
            )),
        }

    def _build_curl(
        self, spec: RequestSpec, auth_label: str, comparison: ComparisonResult
    ) -> str:
        parts = ["curl"]
        if spec.method != "GET":
            parts.append(f"-X {spec.method}")
        if comparison.baseline.headers:
            for k, v in comparison.baseline.headers.items():
                if k.lower() in ("authorization", "cookie"):
                    parts.append(f"-H '{k}: <redacted>'")
                elif k.lower() not in ("content-length", "host"):
                    parts.append(f"-H '{k}: {v}'")
        for k, v in spec.params.items():
            if spec.method in ("POST", "PUT", "PATCH"):
                parts.append(f"-d '{k}={v}'")
        parts.append(f"'{spec.url}'")
        return " \\\n  ".join(parts)
