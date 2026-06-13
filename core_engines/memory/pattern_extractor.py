"""
Pattern extractor: learn vulnerability patterns from confirmed findings.

Converts findings + evidence into reusable patterns for cross-target learning.
"""
import re
from typing import Any, Dict, List, Optional


class PatternExtractor:
    """Extract and normalize vulnerability patterns from findings."""

    # Patterns for endpoint normalization
    UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
    NUMERIC_ID_PATTERN = re.compile(r"/(\d+)(?:/|$)")
    HEX_PATTERN = re.compile(r"0x[0-9a-f]{2,}")

    # Known entity patterns
    ENTITY_KEYWORDS = {
        "user": ["user", "users", "profile", "account", "member", "person"],
        "organization": ["org", "organization", "company", "team", "workspace"],
        "file": ["file", "files", "document", "upload", "attachment"],
        "billing": ["billing", "invoice", "payment", "subscription"],
        "admin": ["admin", "dashboard", "management", "staff"],
        "data": ["data", "export", "report", "download", "backup"],
    }

    @staticmethod
    def normalize_endpoint_path(path: str) -> str:
        """
        Normalize endpoint path by replacing IDs with placeholders.
        
        Examples:
        - /api/users/123 → /api/users/{numeric_id}
        - /api/orgs/uuid-here → /api/orgs/{uuid}
        - /api/items/0xabc123 → /api/items/{hex}
        """
        normalized = path

        # Replace UUIDs
        normalized = PatternExtractor.UUID_PATTERN.sub("{uuid}", normalized)

        # Replace hex IDs
        normalized = PatternExtractor.HEX_PATTERN.sub("{hex}", normalized)

        # Replace numeric IDs
        normalized = re.sub(r"/(\d+)(?=/|$)", "/{numeric_id}", normalized)

        return normalized

    @staticmethod
    def detect_entity_type(path: str, params: Dict[str, Any]) -> Optional[str]:
        """Detect entity type from path and params."""
        combined = f"{path} {str(params)}".lower()

        for entity_type, keywords in PatternExtractor.ENTITY_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                return entity_type

        return None

    @staticmethod
    def detect_auth_smells(params: Dict[str, Any], sensitive_fields: List[str]) -> List[str]:
        """Detect auth-related smells from parameters and response fields."""
        smells = []

        param_names = [str(k).lower() for k in params.keys()] if params else []
        param_str = " ".join(param_names)

        # Check for ownership params
        ownership_keywords = ["user_id", "account_id", "org_id", "team_id", "member_id"]
        if any(kw in param_str for kw in ownership_keywords):
            smells.append("ownership_parameter")

        # Check for sensitive fields in response
        if "email" in sensitive_fields or "phone" in sensitive_fields:
            smells.append("pii_exposure")
        if "token" in sensitive_fields or "password" in sensitive_fields:
            smells.append("credential_exposure")
        if "admin" in sensitive_fields or "role" in sensitive_fields:
            smells.append("privilege_disclosure")

        return smells

    @staticmethod
    def extract_mutation_patterns(
        attempts: List[Dict[str, Any]],
        successful_mutations: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """
        Extract successful mutation patterns from validation attempts.
        
        Returns list of successful mutations with confidence scores.
        """
        patterns = []

        for mutation_key, mutation_value in successful_mutations.items():
            # Count how many attempts this mutation was applied
            if not attempts:
                confidence = 0.5
            else:
                successful = sum(1 for a in attempts if a.get("consistent"))
                confidence = successful / len(attempts) if attempts else 0.5

            patterns.append({
                "mutation_key": mutation_key,
                "mutation_value": mutation_value,
                "confidence": confidence,
                "type": "parameter_swap",  # Could also be header_mutation, path_mutation
            })

        return patterns

    @staticmethod
    def extract_vulnerability_pattern(
        finding_title: str,
        endpoint_path: str,
        endpoint_method: str,
        endpoint_params: Dict[str, Any],
        passed_rules: List[str],
        sensitive_fields: List[str],
        auth_smells: List[str],
        mutation_patterns: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Extract complete vulnerability pattern from finding.
        
        Returns dict suitable for pattern library storage.
        """
        vuln_type = "unknown"
        if "privilege_boundary_break" in passed_rules:
            vuln_type = "idor"
        elif "auth_bypass" in passed_rules:
            vuln_type = "auth_bypass"
        elif "sensitive_data_exposure" in passed_rules:
            vuln_type = "data_exposure"
        elif "cross_session_mismatch" in passed_rules:
            vuln_type = "privilege_escalation"

        entity_type = PatternExtractor.detect_entity_type(endpoint_path, endpoint_params)

        return {
            "vulnerability_type": vuln_type,
            "endpoint_regex": PatternExtractor.normalize_endpoint_path(endpoint_path),
            "endpoint_method": endpoint_method,
            "entity_type": entity_type or "unknown",
            "auth_smells": auth_smells,
            "sensitive_fields_exposed": sensitive_fields,
            "successful_mutations": mutation_patterns,
            "passed_rules": passed_rules,
            "confidence_factors": {
                "rule_count": len(passed_rules),
                "auth_smell_count": len(auth_smells),
                "sensitive_field_count": len(sensitive_fields),
            },
        }

    @staticmethod
    def find_similar_patterns(
        new_pattern: Dict[str, Any],
        pattern_library: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Find similar patterns in library by comparing:
        - Normalized endpoint paths (regex match)
        - Entity type
        - Vulnerability type
        - Auth smells
        
        Returns list of similar patterns (best matches first).
        """
        similar = []

        new_endpoint_regex = new_pattern.get("endpoint_regex", "")
        new_entity_type = new_pattern.get("entity_type", "")
        new_vuln_type = new_pattern.get("vulnerability_type", "")
        new_smells = set(new_pattern.get("auth_smells", []))

        for existing in pattern_library:
            score = 0

            # Endpoint similarity (naive: check if regex patterns are close)
            if existing.get("endpoint_regex") == new_endpoint_regex:
                score += 3
            elif "/".join(new_endpoint_regex.split("/")[:3]) == "/".join(
                existing.get("endpoint_regex", "").split("/")[:3]
            ):
                score += 1

            # Entity type match
            if existing.get("entity_type") == new_entity_type:
                score += 2

            # Vulnerability type match
            if existing.get("vulnerability_type") == new_vuln_type:
                score += 3

            # Auth smell overlap
            existing_smells = set(existing.get("auth_smells", []))
            smell_overlap = len(new_smells & existing_smells)
            score += smell_overlap

            if score >= 2:  # Threshold for similarity
                similar.append({
                    "pattern": existing,
                    "similarity_score": score,
                })

        # Sort by similarity score
        similar.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar
