"""
Execution hardening layer: detect network behavior anomalies and adapt strategy.

Prevents false negatives/positives from WAF, throttling, timeouts, rate limiting.
"""
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class NetworkBehaviorMetadata:
    """Metadata about detected network behavior anomalies."""
    has_rate_limit: bool = False
    has_waf_blocking: bool = False  # none | weak | strong
    waf_strength: str = "none"
    has_timeout: bool = False
    has_throttle_escalation: bool = False
    detected_patterns: List[str] = None
    recommendation: str = "continue"  # continue | backoff | abort
    
    def __post_init__(self):
        if self.detected_patterns is None:
            self.detected_patterns = []


class NetworkBehaviorDetector:
    """Detect network anomalies (WAF, rate limiting, throttling, timeouts)."""

    # Rate limit detection patterns
    RATE_LIMIT_STATUS_CODES = {429, 503, 502}
    RATE_LIMIT_KEYWORDS = [
        r"rate.?limit",
        r"too.?many",
        r"quota",
        r"throttle",
        r"please try again",
    ]

    # WAF detection patterns
    WAF_STATUS_CODES = {403, 401, 410}
    WAF_KEYWORDS = [
        r"WAF",
        r"blocked",
        r"forbidden",
        r"suspended",
        r"access.?denied",
        r"permission",
        r"unauthorized",
    ]

    WEAK_WAF_KEYWORDS = [
        r"not found",
        r"404",
        r"invalid",
        r"incorrect",
    ]

    def detect_rate_limiting(self, status_code: int, body: str, headers: Dict[str, str]) -> bool:
        """Detect rate limiting from response."""
        if status_code in self.RATE_LIMIT_STATUS_CODES:
            return True

        body_lower = body.lower()
        headers_lower = {k.lower(): v.lower() for k, v in headers.items()}

        for pattern in self.RATE_LIMIT_KEYWORDS:
            if re.search(pattern, body_lower, re.IGNORECASE):
                return True
            # Check headers too
            for key, val in headers_lower.items():
                if re.search(pattern, val, re.IGNORECASE):
                    return True

        # Check RateLimit-* headers
        if any(k.startswith("x-ratelimit") or k.startswith("ratelimit") for k in headers_lower):
            return True

        return False

    def detect_waf_blocking(self, status_code: int, body: str, headers: Dict[str, str]) -> str:
        """
        Detect WAF blocking.
        
        Returns: "none" | "weak" | "strong"
        """
        body_lower = body.lower()
        headers_lower = {k.lower(): v.lower() for k, v in headers.items()}

        # Strong WAF indicators
        if status_code in self.WAF_STATUS_CODES:
            for pattern in self.WAF_KEYWORDS:
                if re.search(pattern, body_lower, re.IGNORECASE):
                    return "strong"
                for key, val in headers_lower.items():
                    if re.search(pattern, val, re.IGNORECASE):
                        return "strong"

        # Weak WAF indicators (could be legitimate 404)
        if status_code in {403, 404}:
            for pattern in self.WEAK_WAF_KEYWORDS:
                if re.search(pattern, body_lower, re.IGNORECASE):
                    return "weak"

        return "none"

    def detect_timeout_pattern(self, responses: List[Dict[str, Any]]) -> bool:
        """Detect if there's a pattern of consecutive timeouts."""
        if not responses or len(responses) < 2:
            return False

        timeout_count = sum(1 for r in responses if r.get("has_timeout", False))
        return timeout_count >= len(responses) * 0.5

    def detect_throttle_escalation(self, responses: List[Dict[str, Any]]) -> bool:
        """
        Detect if response times are escalating (sign of throttling).
        
        Pattern: response times increasing across attempts.
        """
        if not responses or len(responses) < 2:
            return False

        elapsed_times = [r.get("elapsed_ms", 0) for r in responses]
        if not elapsed_times:
            return False

        # Check if times are consistently increasing
        increases = 0
        for i in range(1, len(elapsed_times)):
            if elapsed_times[i] > elapsed_times[i - 1]:
                increases += 1

        # If 2+ consecutive increases, flag as escalation
        return increases >= len(elapsed_times) - 2

    def analyze(
        self,
        status_code: int,
        body: str,
        headers: Dict[str, str],
        elapsed_ms: int,
        error: Optional[str] = None,
    ) -> NetworkBehaviorMetadata:
        """
        Analyze response for all anomalies.
        
        Returns NetworkBehaviorMetadata with detected patterns and recommendation.
        """
        metadata = NetworkBehaviorMetadata()

        # Check for rate limiting
        if self.detect_rate_limiting(status_code, body, headers):
            metadata.has_rate_limit = True
            metadata.detected_patterns.append("rate_limit")
            metadata.recommendation = "backoff"

        # Check for WAF blocking
        waf_level = self.detect_waf_blocking(status_code, body, headers)
        if waf_level != "none":
            metadata.has_waf_blocking = True
            metadata.waf_strength = waf_level
            metadata.detected_patterns.append(f"waf_{waf_level}")
            if waf_level == "strong":
                metadata.recommendation = "abort"
            else:
                metadata.recommendation = "backoff"

        # Check for timeout
        if error and "timeout" in error.lower():
            metadata.has_timeout = True
            metadata.detected_patterns.append("timeout")
            if metadata.recommendation == "continue":
                metadata.recommendation = "backoff"

        return metadata


class AdaptiveRetryStrategy:
    """
    Adaptive retry strategy with exponential backoff + jitter.
    
    Decides whether to retry and calculates appropriate delays.
    """

    # Max retries by endpoint pattern (conservative)
    RETRY_BUDGET = {
        "admin": 1,           # Admin endpoints: low tolerance
        "auth": 2,            # Auth endpoints: medium tolerance
        "api": 3,             # API endpoints: higher tolerance
        "safe": 5,            # Safe methods (GET, HEAD): high tolerance
    }

    def __init__(self, base_timeout: int = 15):
        self._base_timeout = base_timeout
        self._request_history: Dict[str, List[Dict]] = {}

    def should_retry(
        self,
        response_metadata: NetworkBehaviorMetadata,
        attempt: int,
        endpoint_pattern: Optional[str] = None,
    ) -> bool:
        """
        Decide whether to retry based on network behavior.
        
        Args:
            response_metadata: Detected anomalies
            attempt: Current attempt number (1-indexed)
            endpoint_pattern: Pattern of endpoint (admin|auth|api|safe)
        
        Returns: True if should retry, False if should stop
        """
        # Never retry if WAF strong block detected
        if response_metadata.waf_strength == "strong":
            return False

        # Get budget for this endpoint
        max_retries = self.RETRY_BUDGET.get(endpoint_pattern or "api", 3)

        # If we've exhausted budget, don't retry
        if attempt >= max_retries:
            return False

        # Retry if rate limit or weak WAF detected
        if response_metadata.has_rate_limit or response_metadata.waf_strength == "weak":
            return True

        # Retry if timeout (up to budget)
        if response_metadata.has_timeout:
            return True

        return False

    def calculate_backoff(
        self,
        attempt: int,
        base_delay: float = 0.5,
        max_delay: float = 30.0,
        jitter: bool = True,
    ) -> float:
        """
        Calculate exponential backoff with optional jitter.
        
        Formula: base_delay * (2 ^ (attempt - 1)) + random jitter
        
        Args:
            attempt: Current attempt (1-indexed)
            base_delay: Base delay in seconds
            max_delay: Cap on delay
            jitter: Add random jitter
        
        Returns: Delay in seconds
        """
        import random

        # Exponential: 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 30.0 (capped)
        exponential = base_delay * (2 ** (attempt - 1))
        delay = min(exponential, max_delay)

        if jitter:
            # Add up to 20% random jitter
            jitter_amount = delay * 0.2 * random.random()
            delay += jitter_amount

        return delay

    def max_retries_for_endpoint(self, endpoint: Dict[str, str]) -> int:
        """
        Determine max retries for an endpoint based on its characteristics.
        
        Conservative approach:
        - Admin endpoints: 1 retry
        - Auth endpoints: 2 retries
        - Standard API: 3 retries
        - Safe methods (GET/HEAD): 5 retries
        """
        path = endpoint.get("path", "").lower()
        method = endpoint.get("method", "GET").upper()

        # Check endpoint type
        if "admin" in path or "dashboard" in path:
            return self.RETRY_BUDGET["admin"]
        elif "auth" in path or "login" in path:
            return self.RETRY_BUDGET["auth"]
        elif method in {"GET", "HEAD", "OPTIONS"}:
            return self.RETRY_BUDGET["safe"]
        else:
            return self.RETRY_BUDGET["api"]

    def get_request_mutation(
        self,
        attempt: int,
        base_headers: Dict[str, str],
    ) -> Dict[str, str]:
        """
        Generate request mutations for retry (vary headers for bypass).
        
        Conservative approach: only vary User-Agent, not payloads.
        
        Args:
            attempt: Attempt number (for mutation variety)
            base_headers: Original headers
        
        Returns: Mutated headers dict
        """
        import random

        mutated = dict(base_headers)

        # Vary User-Agent by attempt
        user_agents = [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "curl/7.68.0",
        ]

        mutated["User-Agent"] = user_agents[attempt % len(user_agents)]

        # Optionally vary Accept header
        if "Accept" in mutated:
            if attempt % 2 == 0:
                mutated["Accept"] = "application/json, */*"
            else:
                mutated["Accept"] = "*/*"

        return mutated

    def record_response(self, domain: str, response_metadata: NetworkBehaviorMetadata) -> None:
        """Record response metadata for detecting escalation patterns."""
        if domain not in self._request_history:
            self._request_history[domain] = []

        self._request_history[domain].append({
            "timestamp": time.time(),
            "metadata": response_metadata,
        })

        # Keep only last 20 requests per domain
        if len(self._request_history[domain]) > 20:
            self._request_history[domain] = self._request_history[domain][-20:]

    def detect_escalation_for_domain(self, domain: str) -> bool:
        """Check if domain is showing escalation pattern (throttle ramping up)."""
        if domain not in self._request_history or len(self._request_history[domain]) < 2:
            return False

        history = self._request_history[domain]
        rate_limit_count = sum(
            1 for entry in history if entry["metadata"].has_rate_limit
        )
        timeout_count = sum(
            1 for entry in history if entry["metadata"].has_timeout
        )

        # If 2+ rate limits or 2+ timeouts in recent history, flag escalation
        return rate_limit_count >= 2 or timeout_count >= 2
