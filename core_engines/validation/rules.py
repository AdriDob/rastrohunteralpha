from dataclasses import dataclass, field
from typing import Dict, List

from core_engines.validation.replayer import ComparisonResult


CRITICAL_SENSITIVE_FIELDS = {
    "email", "ssn", "credit_card", "passport", "jwt",
}

NON_CRITICAL_SENSITIVE_FIELDS = {
    "phone", "role", "billing", "admin", "superuser",
    "staff", "moderator", "secret", "token", "password",
    "apikey", "api_key", "subscription", "payment",
    "invoice",
}


@dataclass
class RuleResult:
    passed: bool
    reason: str
    evidence: List[str]
    confidence_contribution: float


@dataclass
class ValidationReport:
    passed: bool
    passed_rules: List[str]
    failed_rules: List[str]
    details: Dict[str, RuleResult]


class ValidationRuleSet:
    def evaluate(self, results: List[ComparisonResult]) -> ValidationReport:
        rules: Dict[str, RuleResult] = {
            "privilege_boundary_break": self.rule_privilege_boundary_break(results),
            "auth_bypass": self.rule_auth_bypass(results),
            "sensitive_data_exposure": self.rule_sensitive_data_exposure(results),
            "cross_session_mismatch": self.rule_cross_session_mismatch(results),
        }
        passed_rules = [name for name, r in rules.items() if r.passed]
        failed_rules = [name for name, r in rules.items() if not r.passed]
        return ValidationReport(
            passed=len(passed_rules) > 0,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            details=rules,
        )

    def rule_privilege_boundary_break(self, results: List[ComparisonResult]) -> RuleResult:
        if len(results) < 3:
            return RuleResult(
                passed=False, reason="Insufficient attempts (< 3).",
                evidence=[], confidence_contribution=0.0,
            )
        all_status_match = all(r.status_match for r in results)
        max_diff = max(r.body_diff_ratio for r in results)
        all_have_sensitive = all(
            len(r.sensitive_fields_detected) > 0 for r in results
        )
        all_consistent = all(r.consistent for r in results)

        if all_status_match and max_diff < 0.25 and all_have_sensitive and all_consistent:
            fields = sorted(set(
                f for r in results for f in r.sensitive_fields_detected
            ))
            return RuleResult(
                passed=True,
                reason=(
                    f"Privilege boundary break: {len(results)}/3 consistent, "
                    f"status match ({all_status_match}), "
                    f"body diff {max_diff:.2f}, "
                    f"sensitive fields: {fields}"
                ),
                evidence=[f"attempt_{r.attempt}" for r in results],
                confidence_contribution=0.25,
            )
        fail_reasons = []
        if not all_status_match:
            fail_reasons.append("status codes differ across attempts")
        if max_diff >= 0.25:
            fail_reasons.append(f"body diff {max_diff:.2f} >= 0.25 threshold")
        if not all_have_sensitive:
            fail_reasons.append("no sensitive fields detected consistently")
        if not all_consistent:
            fail_reasons.append("inconsistent across attempts")
        return RuleResult(
            passed=False,
            reason="; ".join(fail_reasons) or "privilege_boundary_break rule not met",
            evidence=[r.attempt for r in results if not r.consistent],
            confidence_contribution=0.0,
        )

    def rule_auth_bypass(self, results: List[ComparisonResult]) -> RuleResult:
        if len(results) < 3:
            return RuleResult(
                passed=False, reason="Insufficient attempts (< 3).",
                evidence=[], confidence_contribution=0.0,
            )
        all_probe_ok = all(r.probe.status_code == 200 for r in results)
        all_baseline_ok = all(r.baseline.status_code == 200 for r in results)
        max_diff = max(r.body_diff_ratio for r in results)
        all_consistent = all(r.consistent for r in results)

        if all_probe_ok and all_baseline_ok and max_diff < 0.40 and all_consistent:
            return RuleResult(
                passed=True,
                reason=(
                    f"Auth bypass: probe (no auth) returned 200 matching baseline "
                    f"(diff {max_diff:.2f}), {len(results)}/3 consistent"
                ),
                evidence=[f"attempt_{r.attempt}" for r in results],
                confidence_contribution=0.25,
            )
        fail_reasons = []
        if not all_probe_ok:
            statuses = {r.probe.status_code for r in results}
            fail_reasons.append(f"probe status codes {statuses} (expected 200)")
        if not all_baseline_ok:
            statuses = {r.baseline.status_code for r in results}
            fail_reasons.append(f"baseline status codes {statuses} (expected 200)")
        if max_diff >= 0.40:
            fail_reasons.append(f"body diff {max_diff:.2f} >= 0.40")
        if not all_consistent:
            fail_reasons.append("inconsistent across attempts")
        return RuleResult(
            passed=False,
            reason="; ".join(fail_reasons) or "auth_bypass rule not met",
            evidence=[], confidence_contribution=0.0,
        )

    def rule_sensitive_data_exposure(self, results: List[ComparisonResult]) -> RuleResult:
        if len(results) < 3:
            return RuleResult(
                passed=False, reason="Insufficient attempts (< 3).",
                evidence=[], confidence_contribution=0.0,
            )
        for result in results:
            critical = [
                f for f in result.sensitive_fields_detected
                if f in CRITICAL_SENSITIVE_FIELDS
            ]
            non_critical = [
                f for f in result.sensitive_fields_detected
                if f in NON_CRITICAL_SENSITIVE_FIELDS
            ]
            if len(critical) >= 1 or len(non_critical) >= 3:
                return RuleResult(
                    passed=True,
                    reason=(
                        f"Sensitive data exposure in attempt {result.attempt}: "
                        f"{len(critical)} critical, {len(non_critical)} non-critical fields. "
                        f"Fields: {result.sensitive_fields_detected}"
                    ),
                    evidence=[f"attempt_{result.attempt}"],
                    confidence_contribution=0.25,
                )
        all_fields = sorted(set(
            f for r in results for f in r.sensitive_fields_detected
        ))
        return RuleResult(
            passed=False,
            reason=(
                f"No sensitive data exposure threshold met. "
                f"Fields found across attempts: {all_fields}"
            ),
            evidence=[], confidence_contribution=0.0,
        )

    def rule_cross_session_mismatch(self, results: List[ComparisonResult]) -> RuleResult:
        if len(results) < 3:
            return RuleResult(
                passed=False, reason="Insufficient attempts (< 3).",
                evidence=[], confidence_contribution=0.0,
            )
        all_status_match = all(r.status_match for r in results)
        all_consistent = all(r.consistent for r in results)
        min_diff = min(r.body_diff_ratio for r in results)
        no_rate_limit = not any(r.has_rate_limit for r in results)
        no_timeout = not any(r.has_timeout for r in results)

        if all_status_match and all_consistent and min_diff >= 0.15 and no_rate_limit and no_timeout:
            return RuleResult(
                passed=True,
                reason=(
                    f"Cross-session mismatch: body diff {min_diff:.2f} minimum, "
                    f"{len(results)}/3 consistent, status match, no rate limit"
                ),
                evidence=[f"attempt_{r.attempt}" for r in results],
                confidence_contribution=0.25,
            )
        fail_reasons = []
        if not all_status_match:
            fail_reasons.append("status mismatch")
        if min_diff < 0.15:
            fail_reasons.append(f"min diff {min_diff:.2f} < 0.15")
        if not all_consistent:
            fail_reasons.append("inconsistent")
        if not no_rate_limit:
            fail_reasons.append("rate limited")
        if not no_timeout:
            fail_reasons.append("timeout detected")
        return RuleResult(
            passed=False,
            reason="; ".join(fail_reasons) or "cross_session_mismatch rule not met",
            evidence=[], confidence_contribution=0.0,
        )
