from typing import Dict


def should_deprioritize(metadata: Dict) -> bool:
    # deprioritize when noise is high or quality is very low
    noise = metadata.get("noise_level", 0)
    quality = metadata.get("quality_score", 50)
    static = metadata.get("static", False)
    if static and quality < 40:
        return True
    if noise >= 50:
        return True
    if quality < 30:
        return True
    return False


def should_prioritize(metadata: Dict) -> bool:
    # prioritize API-heavy, SaaS, GraphQL, admin or multi-tenant
    if metadata.get("graphql"):
        return True
    if metadata.get("api_count", 0) >= 3:
        return True
    if metadata.get("saas_prob", 0) > 0.6:
        return True
    if metadata.get("admin") or metadata.get("multi_tenant"):
        return True
    return False
