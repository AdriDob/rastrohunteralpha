from typing import Any


def filter_targets_by_min_quality(targets: list[dict[str, Any]], min_quality: int = 30) -> list[dict[str, Any]]:
    return [t for t in targets if t.get("quality_score", 50) >= min_quality]


def filter_targets_by_max_complexity(targets: list[dict[str, Any]], max_complexity: int = 70) -> list[dict[str, Any]]:
    return [t for t in targets if t.get("complexity", 50) <= max_complexity]


def filter_targets_by_platform(targets: list[dict[str, Any]], platform: str) -> list[dict[str, Any]]:
    return [t for t in targets if t.get("platform", "").lower() == platform.lower()]


def should_deprioritize(metadata: dict) -> bool:
    # deprioritize when noise is high or quality is very low
    noise = metadata.get("noise_level", 0)
    quality = metadata.get("quality_score", 50)
    static = metadata.get("static", False)
    if static and quality < 40:
        return True
    if noise >= 50:
        return True
    return quality < 30


def should_prioritize(metadata: dict) -> bool:
    # prioritize API-heavy, SaaS, GraphQL, admin or multi-tenant
    if metadata.get("graphql"):
        return True
    if metadata.get("api_count", 0) >= 3:
        return True
    if metadata.get("saas_prob", 0) > 0.6:
        return True
    return bool(metadata.get("admin") or metadata.get("multi_tenant"))
