import json
from datetime import datetime, timedelta
from typing import Any

from core_engines.memory.learning_scorer import LearningScorer, PayoutEstimator
from core_engines.memory.pattern_extractor import PatternExtractor
from database.db import SessionLocal
from database.models import MemoryRecord


class MemoryPatternLibrary:
    """
    Global pattern library: learns from confirmed findings, reuses patterns.

    Supports:
    - Store/query vulnerability patterns
    - Learn from confirmed findings
    - Find similar patterns across targets
    - Estimate payouts based on history
    """

    RETENTION_DAYS = 90

    def __init__(self):
        self._extractor = PatternExtractor()
        self._scorer = LearningScorer()

    def _session(self):
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def record_confirmed_finding(
        self,
        finding_title: str,
        endpoint_path: str,
        endpoint_method: str,
        endpoint_params: dict[str, Any],
        passed_rules: list[str],
        sensitive_fields: list[str],
        successful_mutations: dict[str, str],
    ) -> dict[str, Any]:
        """
        Record a confirmed finding and extract pattern.

        Stores pattern in memory for future matching.
        """
        # Extract pattern
        auth_smells = PatternExtractor.detect_auth_smells(
            endpoint_params, sensitive_fields
        )
        mutation_patterns = PatternExtractor.extract_mutation_patterns(
            [], successful_mutations
        )

        pattern = PatternExtractor.extract_vulnerability_pattern(
            finding_title=finding_title,
            endpoint_path=endpoint_path,
            endpoint_method=endpoint_method,
            endpoint_params=endpoint_params,
            passed_rules=passed_rules,
            sensitive_fields=sensitive_fields,
            auth_smells=auth_smells,
            mutation_patterns=mutation_patterns,
        )

        # Store in memory
        for sess in self._session():
            record = MemoryRecord(
                category="vuln_pattern",
                key=f"{pattern['vulnerability_type']}:{pattern['entity_type']}",
                details=json.dumps(pattern),
            )
            sess.add(record)
            break

        return pattern

    def record_endpoint_profile(
        self,
        endpoint_path: str,
        endpoint_method: str,
        labels: list[str],
        risk_score: float,
        target_name: str,
    ) -> None:
        """Record endpoint profile for comparison across targets."""
        normalized_path = PatternExtractor.normalize_endpoint_path(endpoint_path)

        profile = {
            "path": endpoint_path,
            "normalized_path": normalized_path,
            "method": endpoint_method,
            "labels": labels,
            "risk_score": risk_score,
            "target": target_name,
            "timestamp": datetime.now().isoformat(),
        }

        for sess in self._session():
            record = MemoryRecord(
                category="endpoint_profile",
                key=f"{target_name}:{normalized_path}",
                details=json.dumps(profile),
            )
            sess.add(record)
            break

    def find_similar_endpoints(
        self,
        endpoint_path: str,
        entity_type: str | None,
        auth_smells: list[str],
        current_target: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Find similar endpoints in OTHER targets.

        Returns endpoints that might be vulnerable to the same pattern.
        """
        normalized = PatternExtractor.normalize_endpoint_path(endpoint_path)

        for sess in self._session():
            profiles = (
                sess.query(MemoryRecord)
                .filter(MemoryRecord.category == "endpoint_profile")
                .all()
            )
            break

        similar = []
        for record in profiles:
            try:
                profile = json.loads(record.details)

                # Skip same target
                if current_target and profile.get("target") == current_target:
                    continue

                # Check normalized path similarity
                profile_normalized = profile.get("normalized_path", "")
                if profile_normalized == normalized:
                    similarity_score = 3
                elif normalized.split("/")[1:3] == profile_normalized.split("/")[1:3]:
                    similarity_score = 1
                else:
                    similarity_score = 0

                # Check auth smell overlap
                profile_auth_smells = profile.get("auth_smells", [])
                smell_overlap = len(set(auth_smells) & set(profile_auth_smells))

                total_score = similarity_score + smell_overlap
                if total_score >= 1:
                    similar.append({
                        "profile": profile,
                        "similarity": total_score,
                    })
            except json.JSONDecodeError:
                continue

        # Sort by similarity
        similar.sort(key=lambda x: x["similarity"], reverse=True)
        return similar

    def get_payload_template(
        self,
        vulnerability_type: str,
        endpoint_entity: str,
    ) -> list[dict[str, Any]] | None:
        """
        Get successful mutation templates for this vuln type.

        Returns list of successful mutations from similar findings.
        """
        for sess in self._session():
            patterns = (
                sess.query(MemoryRecord)
                .filter(MemoryRecord.category == "vuln_pattern")
                .all()
            )
            break

        templates = []
        for record in patterns:
            try:
                pattern = json.loads(record.details)

                if (
                    pattern.get("vulnerability_type") == vulnerability_type
                    and pattern.get("entity_type") == endpoint_entity
                ):
                    mutations = pattern.get("successful_mutations", [])
                    if mutations:
                        templates.extend(mutations)
            except json.JSONDecodeError:
                continue

        return templates if templates else None

    def boost_endpoint_score(
        self,
        base_confidence: float,
        endpoint_path: str,
        entity_type: str | None,
        vuln_type: str,
        severity: str,
    ) -> dict[str, Any]:
        """
        Boost endpoint confidence based on pattern library.

        Returns dict with boosted confidence and reasoning.
        """
        # Find similar patterns
        normalized_path = PatternExtractor.normalize_endpoint_path(endpoint_path)

        for sess in self._session():
            patterns = (
                sess.query(MemoryRecord)
                .filter(MemoryRecord.category == "vuln_pattern")
                .all()
            )
            break

        similar_patterns = []
        for record in patterns:
            try:
                pattern = json.loads(record.details)
                if pattern.get("endpoint_regex") == normalized_path:
                    similar_patterns.append({"pattern": pattern, "similarity_score": 3})
            except json.JSONDecodeError:
                continue

        # Apply learning scorer
        result = self._scorer.score_endpoint_with_learning(
            base_confidence=base_confidence,
            endpoint_path=endpoint_path,
            entity_type=entity_type,
            vuln_type=vuln_type,
            severity=severity,
            similar_patterns=similar_patterns,
        )

        return result

    def estimate_payout(
        self,
        finding_type: str,
        severity: str,
        entity_type: str | None,
    ) -> float:
        """Estimate payout for finding based on type and history."""
        for sess in self._session():
            historical_payouts = (
                sess.query(MemoryRecord)
                .filter(MemoryRecord.category == "finding_payout")
                .filter(MemoryRecord.key == f"{finding_type}:{entity_type}")
                .all()
            )
            break

        payouts = []
        for record in historical_payouts:
            try:
                details = json.loads(record.details)
                if "amount" in details:
                    payouts.append(float(details["amount"]))
            except (json.JSONDecodeError, ValueError):
                continue

        # Estimate
        estimator = PayoutEstimator()
        return estimator.estimate_payout(
            vuln_type=finding_type,
            severity=severity,
            entity_type=entity_type,
            historical_payouts=payouts,
        )

    def record_payout(
        self,
        finding_type: str,
        entity_type: str | None,
        amount: float,
    ) -> None:
        """Record actual payout for learning."""
        for sess in self._session():
            record = MemoryRecord(
                category="finding_payout",
                key=f"{finding_type}:{entity_type}",
                details=json.dumps({"amount": amount, "timestamp": datetime.now().isoformat()}),
            )
            sess.add(record)
            break

    def cleanup_old_records(self) -> int:
        """Remove records older than retention period."""
        cutoff = datetime.now() - timedelta(days=self.RETENTION_DAYS)

        for sess in self._session():
            deleted = (
                sess.query(MemoryRecord)
                .filter(MemoryRecord.created_at < cutoff)
                .delete()
            )
            break

        return deleted

    def close(self):
        pass  # sessions are per-method now


# Backwards compatibility: original MemoryEngine still available
class MemoryEngine:
    def _session(self):
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def remember(
        self, category: str, key: str, details: dict[str, Any]
    ) -> MemoryRecord:
        record = MemoryRecord(category=category, key=key, details=str(details))
        for sess in self._session():
            sess.add(record)
            sess.commit()
            sess.refresh(record)
            return record
        return record

    def recent(self, category: str, limit: int = 20) -> list[MemoryRecord]:
        for sess in self._session():
            result = (
                sess.query(MemoryRecord)
                .filter(MemoryRecord.category == category)
                .order_by(MemoryRecord.created_at.desc())
                .limit(limit)
                .all()
            )
            return result
        return []

    def close(self):
        pass  # sessions are per-method now
