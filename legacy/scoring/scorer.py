from typing import Dict, Any


class Scorer:
    """
    Tactical scoring engine focused on:
    - IDOR/BOLA exposure
    - multi-tenant weaknesses
    - auth boundary failures
    - enterprise ROI
    """

    def score_target(self, meta: Dict[str, Any] = None) -> Dict[str, float]:
        meta = meta or {}

        score = 0.0

        # SaaS environments are higher value
        if meta.get("is_saas"):
            score += 20.0

        # APIs usually expose attack surface
        if meta.get("has_api"):
            score += 25.0

        # Multi-tenant systems are ideal for BOLA/IDOR
        if meta.get("multi_tenant"):
            score += 30.0

        # Admin panels often expose privilege boundaries
        if meta.get("has_admin"):
            score += 20.0

        # GraphQL often increases attack complexity and exposure
        if meta.get("has_graphql"):
            score += 15.0

        # Enterprise environments generally pay better
        if meta.get("enterprise"):
            score += 15.0

        # Internal APIs can expose trust boundaries
        if meta.get("internal_api"):
            score += 15.0

        quality = min(score, 100.0)

        return {
            "priority": quality,
            "saaS_probability": 85.0 if meta.get("is_saas") else 35.0,
            "target_quality": quality,
        }

    def score_endpoint(self, endpoint_meta: Dict[str, Any] = None) -> Dict[str, float]:
        endpoint_meta = endpoint_meta or {}

        score = 0.0

        # EXPORTS = jackpot potential
        if endpoint_meta.get("export"):
            score += 35.0

        # Admin routes
        if endpoint_meta.get("admin"):
            score += 25.0

        # GraphQL surfaces
        if endpoint_meta.get("graphql"):
            score += 20.0

        # Internal-only functionality
        if endpoint_meta.get("internal"):
            score += 20.0

        # UUID references often map to objects/resources
        if endpoint_meta.get("uuid"):
            score += 25.0

        # Numeric IDs are classic IDOR indicators
        if endpoint_meta.get("numeric_id"):
            score += 20.0

        # Auth smells are extremely important
        if endpoint_meta.get("auth_smell"):
            score += 35.0

        # Multi-tenant references
        if endpoint_meta.get("tenant"):
            score += 30.0

        # Organization-scoped resources
        if endpoint_meta.get("organization"):
            score += 25.0

        # Sensitive business areas
        if endpoint_meta.get("billing"):
            score += 20.0

        if endpoint_meta.get("analytics"):
            score += 15.0

        if endpoint_meta.get("attachments"):
            score += 20.0

        if endpoint_meta.get("files"):
            score += 20.0

        # High-value HTTP methods
        method = str(endpoint_meta.get("method", "GET")).upper()

        if method in {"PUT", "PATCH", "DELETE"}:
            score += 15.0

        if method == "POST":
            score += 10.0

        final_score = min(score, 100.0)

        return {
            "priority": final_score,
            "risk_score": final_score,
        }
