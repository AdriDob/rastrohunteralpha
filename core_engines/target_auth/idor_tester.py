from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from core_engines.validation.replayer import AuthContext, RequestReplayer, RequestSpec, ResponseRecord

logger = logging.getLogger("rastro.idor_tester")

IDOR_PARAM_PATTERNS = [
    re.compile(r"\b(id|uid|user_id|account_id|customer_id|profile_id|order_id|invoice_id|document_id|file_id|ticket_id|msg_id|post_id|article_id|product_id|sku|reference|token|key)\b", re.I),
    re.compile(r"/api/(?:v\d+/)?(?:users|accounts|customers|profiles|orders|invoices|documents|files|tickets|messages|posts|articles|products)/(\d+)"),
    re.compile(r"/api/(?:v\d+/)?(?:users|accounts|customers|profiles|orders|invoices|documents|files|tickets|messages|posts|articles|products)/([a-f0-9-]{36})"),
]

SENSITIVE_PATTERNS: Dict[str, re.Pattern] = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
}


@dataclass
class IDORTestResult:
    parameter: str
    original_value: str
    probe_value: str
    baseline_status: int
    probe_status: int
    body_diff_ratio: float
    sensitive_fields_leaked: List[str]
    verdict: str  # vulnerable, blocked, inconclusive
    reason: str


@dataclass
class IDORScanReport:
    target_id: int
    endpoint_id: int
    identity_baseline_id: int
    identity_probe_id: int
    total_tests: int
    vulnerable: List[IDORTestResult]
    blocked: List[IDORTestResult]
    inconclusive: List[IDORTestResult]
    elapsed_ms: int


class IDORTester:
    def __init__(self, replayer: Optional[RequestReplayer] = None):
        self._replayer = replayer or RequestReplayer()

    def _extract_idor_candidates(self, url: str, method: str) -> List[Dict[str, str]]:
        parsed = urlparse(url)
        candidates: List[Dict[str, str]] = []

        for pattern in IDOR_PARAM_PATTERNS[1:]:
            match = pattern.search(url)
            if match and len(match.groups()) > 0:
                candidates.append({
                    "type": "path",
                    "name": "path_id",
                    "original": match.group(1),
                    "location": "path",
                })

        query_params = parse_qs(parsed.query)
        for key, values in query_params.items():
            if IDOR_PARAM_PATTERNS[0].search(key):
                for val in values:
                    if val and len(val) > 1 and val != "0":
                        candidates.append({
                            "type": "query",
                            "name": key,
                            "original": val,
                            "location": "query",
                        })

        return candidates

    def _generate_probe_value(self, original: str) -> str:
        stripped = original.strip()
        if stripped.isdigit():
            val = int(stripped)
            if val <= 1:
                return str(val + 100)
            if val <= 100:
                return str(val + 1000)
            return str(val + 1)
        uuid_match = re.match(r"([a-f0-9-]{36})", stripped, re.I)
        if uuid_match:
            parts = list(uuid_match.group(1))
            for i in range(len(parts) - 1, -1, -1):
                if parts[i] != 'f' and parts[i] != 'F':
                    parts[i] = hex(int(parts[i], 16) + 1)[2:]
                    break
            return ''.join(parts)
        return f"{stripped}_other"

    def _build_probe_spec(self, spec: RequestSpec, candidate: Dict[str, str], probe_val: str) -> RequestSpec:
        url = spec.url
        if candidate["location"] == "path":
            url = url.replace(candidate["original"], probe_val, 1)
        elif candidate["location"] == "query":
            parsed = urlparse(url)
            params = parse_qs(parsed.query, keep_blank_values=True)
            params[candidate["name"]] = [probe_val]
            new_query = urlencode(params, doseq=True)
            url = urlunparse(parsed._replace(query=new_query))

        return RequestSpec(
            url=url,
            method=spec.method,
            headers=dict(spec.headers),
            params=dict(spec.params),
            body=spec.body,
        )

    def _detect_sensitive_leaks(self, body: str) -> List[str]:
        found: List[str] = []
        for label, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(body):
                found.append(label)
        return found

    def scan(
        self,
        target_id: int,
        endpoint_id: int,
        baseline_auth: AuthContext,
        probe_auth: AuthContext,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
    ) -> IDORScanReport:
        start = time.monotonic()
        request_spec = RequestSpec(
            url=url,
            method=method,
            headers=headers or {},
            params=params or {},
            body=body,
        )

        candidates = self._extract_idor_candidates(url, method)
        vulnerable: List[IDORTestResult] = []
        blocked: List[IDORTestResult] = []
        inconclusive: List[IDORTestResult] = []

        for candidate in candidates:
            probe_val = self._generate_probe_value(candidate["original"])
            probe_spec = self._build_probe_spec(request_spec, candidate, probe_val)

            baseline_resp = self._replayer.execute(request_spec, baseline_auth)
            probe_resp = self._replayer.execute(probe_spec, probe_auth)

            if baseline_resp.status_code == 0 or probe_resp.status_code == 0:
                inconclusive.append(IDORTestResult(
                    parameter=candidate["name"],
                    original_value=candidate["original"],
                    probe_value=probe_val,
                    baseline_status=baseline_resp.status_code,
                    probe_status=probe_resp.status_code,
                    body_diff_ratio=0.0,
                    sensitive_fields_leaked=[],
                    verdict="inconclusive",
                    reason="Request error (timeout or circuit breaker)",
                ))
                continue

            body_diff_ratio = 0.0
            longer = max(len(baseline_resp.body), len(probe_resp.body))
            if longer > 0:
                body_diff_ratio = 1.0 - (min(len(baseline_resp.body), len(probe_resp.body)) / longer)

            sensitive_leaks = self._detect_sensitive_leaks(probe_resp.body)

            if probe_resp.status_code == 200 and baseline_resp.status_code in (200, 403, 404):
                if body_diff_ratio < 0.3:
                    verdict = "vulnerable"
                    reason = f"Probe got 200 with similar body to baseline (diff={body_diff_ratio:.2f})"
                    if sensitive_leaks:
                        reason += f", leaked: {', '.join(sensitive_leaks)}"
                    vulnerable.append(IDORTestResult(
                        parameter=candidate["name"],
                        original_value=candidate["original"],
                        probe_value=probe_val,
                        baseline_status=baseline_resp.status_code,
                        probe_status=probe_resp.status_code,
                        body_diff_ratio=round(body_diff_ratio, 4),
                        sensitive_fields_leaked=sensitive_leaks,
                        verdict="vulnerable",
                        reason=reason,
                    ))
                else:
                    inconclusive.append(IDORTestResult(
                        parameter=candidate["name"],
                        original_value=candidate["original"],
                        probe_value=probe_val,
                        baseline_status=baseline_resp.status_code,
                        probe_status=probe_resp.status_code,
                        body_diff_ratio=round(body_diff_ratio, 4),
                        sensitive_fields_leaked=sensitive_leaks,
                        verdict="inconclusive",
                        reason=f"Probe got 200 but body differs significantly (diff={body_diff_ratio:.2f})",
                    ))
            elif probe_resp.status_code in (403, 401):
                blocked.append(IDORTestResult(
                    parameter=candidate["name"],
                    original_value=candidate["original"],
                    probe_value=probe_val,
                    baseline_status=baseline_resp.status_code,
                    probe_status=probe_resp.status_code,
                    body_diff_ratio=round(body_diff_ratio, 4),
                    sensitive_fields_leaked=sensitive_leaks,
                    verdict="blocked",
                    reason=f"Probe got {probe_resp.status_code} — access denied",
                ))
            else:
                inconclusive.append(IDORTestResult(
                    parameter=candidate["name"],
                    original_value=candidate["original"],
                    probe_value=probe_val,
                    baseline_status=baseline_resp.status_code,
                    probe_status=probe_resp.status_code,
                    body_diff_ratio=round(body_diff_ratio, 4),
                    sensitive_fields_leaked=sensitive_leaks,
                    verdict="inconclusive",
                    reason=f"Unexpected status: baseline={baseline_resp.status_code}, probe={probe_resp.status_code}",
                ))

        elapsed = int((time.monotonic() - start) * 1000)
        return IDORScanReport(
            target_id=target_id,
            endpoint_id=endpoint_id,
            identity_baseline_id=0,
            identity_probe_id=0,
            total_tests=len(candidates),
            vulnerable=vulnerable,
            blocked=blocked,
            inconclusive=inconclusive,
            elapsed_ms=elapsed,
        )
