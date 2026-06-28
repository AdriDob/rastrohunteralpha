import hashlib
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests

from core_engines.validation.hardening import (
    AdaptiveRetryStrategy,
    NetworkBehaviorDetector,
)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
DEFAULT_TIMEOUT = 15
MAX_BODY_SIZE = 10240
PACING_DELAY = 0.5
CIRCUIT_COOLDOWN = 30

SENSITIVE_PATTERNS: dict[str, str] = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "jwt": r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
    "passport": r"\b[A-Z]{1,2}\d{6,9}\b",
}

SENSITIVE_KEYWORDS = [
    "admin", "superuser", "staff", "moderator", "role",
    "billing", "invoice", "payment", "subscription",
    "secret", "token", "password", "apikey", "api_key",
]


@dataclass
class RequestSpec:
    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    body: str | None = None


@dataclass
class AuthContext:
    token: str | None = None
    cookies: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    label: str = "anonymous"


@dataclass
class ResponseRecord:
    status_code: int
    headers: dict[str, str]
    body: str
    body_hash: str
    elapsed_ms: int
    error: str | None = None


@dataclass
class ComparisonResult:
    attempt: int
    baseline: ResponseRecord
    probe: ResponseRecord
    status_match: bool
    body_diff_ratio: float
    headers_diff: dict[str, tuple[Any, Any]]
    sensitive_fields_detected: list[str]
    has_rate_limit: bool
    has_timeout: bool
    consistent: bool
    timestamp: str


class RequestReplayer:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT, pacing: float = PACING_DELAY):
        self._timeout = timeout
        self._pacing = pacing
        self._circuit_breakers: dict[str, float] = {}
        self._user_agents = [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
        ]
        # NEW: Hardening layer
        self._behavior_detector = NetworkBehaviorDetector()
        self._retry_strategy = AdaptiveRetryStrategy(base_timeout=timeout)

    def execute(self, request_spec: RequestSpec, auth: AuthContext) -> ResponseRecord:
        domain = urlparse(request_spec.url).netloc
        if self.is_circuit_open(domain):
            return ResponseRecord(
                status_code=0, headers={}, body="",
                body_hash="", elapsed_ms=0,
                error=f"Circuit breaker open for {domain}",
            )

        method = request_spec.method.upper()
        headers = dict(request_spec.headers)
        headers.setdefault("User-Agent", random.choice(self._user_agents))
        headers.update(auth.headers)
        if auth.token:
            headers.setdefault("Authorization", f"Bearer {auth.token}")

        cookies = dict(auth.cookies)
        start = time.monotonic()

        try:
            resp = requests.request(
                method=method,
                url=request_spec.url,
                headers=headers,
                params=request_spec.params,
                data=request_spec.body,
                cookies=cookies,
                timeout=self._timeout,
                allow_redirects=False,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            body_text = resp.text[:MAX_BODY_SIZE]
            body_hash = hashlib.sha256(resp.text.encode()).hexdigest()
            return ResponseRecord(
                status_code=resp.status_code,
                headers=dict(resp.headers),
                body=body_text,
                body_hash=body_hash,
                elapsed_ms=elapsed,
            )
        except requests.exceptions.Timeout:
            self._trip_circuit(domain)
            return ResponseRecord(
                status_code=0, headers={}, body="",
                body_hash="", elapsed_ms=int((time.monotonic() - start) * 1000),
                error="timeout",
            )
        except requests.exceptions.RequestException as e:
            return ResponseRecord(
                status_code=0, headers={}, body="",
                body_hash="", elapsed_ms=int((time.monotonic() - start) * 1000),
                error=str(e)[:200],
            )

    def revalidate(
        self,
        request_spec: RequestSpec,
        auth_baseline: AuthContext,
        auth_probe: AuthContext,
        mutations: dict[str, str],
        min_attempts: int = 3,
    ) -> list[ComparisonResult]:
        """
        Revalidate with adaptive retry strategy (hardening layer).

        NEW: Integrates network behavior detection and exponential backoff.
        """
        results: list[ComparisonResult] = []
        domain = urlparse(request_spec.url).netloc
        endpoint_pattern = self._infer_endpoint_pattern(request_spec.url)
        max_retries = self._retry_strategy.max_retries_for_endpoint({
            "path": request_spec.url,
            "method": request_spec.method,
        })

        actual_max_attempts = max(min_attempts, max_retries)
        attempt = 1

        while attempt <= actual_max_attempts:
            # Pacing before request
            if attempt > 1:
                time.sleep(self._pacing)

            mutated = RequestSpec(
                url=request_spec.url,
                method=request_spec.method,
                headers=dict(request_spec.headers),
                params=dict(request_spec.params),
                body=request_spec.body,
            )
            for key, val in mutations.items():
                mutated.params[key] = val

            # Execute both baseline and probe
            baseline_resp = self.execute(request_spec, auth_baseline)
            probe_resp = self.execute(mutated, auth_probe)

            # Analyze probe response for anomalies
            behavior = self._behavior_detector.analyze(
                status_code=probe_resp.status_code,
                body=probe_resp.body,
                headers=probe_resp.headers,
                elapsed_ms=probe_resp.elapsed_ms,
                error=probe_resp.error,
            )
            self._retry_strategy.record_response(domain, behavior)

            # Create comparison result
            result = self._compare(attempt, baseline_resp, probe_resp)

            # Add hardening metadata
            result.has_rate_limit = behavior.has_rate_limit
            result.has_timeout = behavior.has_timeout

            # Check consistency with previous attempt
            if attempt > 1:
                prev = results[-1]
                result.consistent = (
                    result.status_match == prev.status_match
                    and abs(result.body_diff_ratio - prev.body_diff_ratio) < 0.05
                )
            else:
                result.consistent = True

            results.append(result)

            # Decision: continue, backoff, or abort?
            if behavior.recommendation == "abort":
                # Strong WAF detected: stop retrying
                break
            elif behavior.recommendation == "backoff":
                # Rate limit or weak WAF: check if should retry
                if self._retry_strategy.should_retry(behavior, attempt, endpoint_pattern):
                    backoff_delay = self._retry_strategy.calculate_backoff(attempt)
                    time.sleep(backoff_delay)
                    # Mutate headers for next attempt
                    request_spec.headers.update(
                        self._retry_strategy.get_request_mutation(attempt, request_spec.headers)
                    )
                    attempt += 1
                    continue
                else:
                    # Out of budget, stop
                    break
            else:
                # No anomaly: continue to next attempt normally
                attempt += 1

        return results

    def _infer_endpoint_pattern(self, url: str) -> str:
        """Infer endpoint pattern (admin|auth|api|safe) from URL."""
        path = url.lower()
        if "admin" in path or "dashboard" in path:
            return "admin"
        elif "auth" in path or "login" in path or "oauth" in path:
            return "auth"
        else:
            return "api"

    def is_circuit_open(self, domain: str) -> bool:
        if domain not in self._circuit_breakers:
            return False
        cooldown = self._circuit_breakers[domain]
        if time.monotonic() - cooldown < CIRCUIT_COOLDOWN:
            return True
        del self._circuit_breakers[domain]
        return False

    def reset_circuit(self, domain: str) -> None:
        self._circuit_breakers.pop(domain, None)

    def _trip_circuit(self, domain: str) -> None:
        self._circuit_breakers[domain] = time.monotonic()

    def _compare(
        self, attempt: int, baseline: ResponseRecord, probe: ResponseRecord
    ) -> ComparisonResult:
        status_match = baseline.status_code == probe.status_code

        body_diff_ratio = 0.0
        longer = max(len(baseline.body), len(probe.body))
        if longer > 0:
            shorter = min(len(baseline.body), len(probe.body))
            body_diff_ratio = 1.0 - (shorter / longer)

        headers_diff: dict[str, tuple[Any, Any]] = {}
        all_keys = set(baseline.headers) | set(probe.headers)
        for k in all_keys:
            bv = baseline.headers.get(k)
            pv = probe.headers.get(k)
            if bv != pv:
                headers_diff[k] = (bv, pv)

        sensitive_fields_detected = self._detect_sensitive_fields(probe.body)

        has_rate_limit = (
            probe.status_code == 429
            or any(k.lower() == "retry-after" for k in probe.headers)
        )
        has_timeout = probe.error == "timeout" or baseline.error == "timeout"

        return ComparisonResult(
            attempt=attempt,
            baseline=baseline,
            probe=probe,
            status_match=status_match,
            body_diff_ratio=round(body_diff_ratio, 4),
            headers_diff=headers_diff,
            sensitive_fields_detected=sensitive_fields_detected,
            has_rate_limit=has_rate_limit,
            has_timeout=has_timeout,
            consistent=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _detect_sensitive_fields(self, body: str) -> list[str]:
        found: list[str] = []
        body_lower = body.lower()
        for label, pattern in SENSITIVE_PATTERNS.items():
            if re.search(pattern, body):
                found.append(label)
        for keyword in SENSITIVE_KEYWORDS:
            if keyword in body_lower and keyword not in found:
                found.append(keyword)
        return found
