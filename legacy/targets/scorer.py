from typing import Dict


def clamp(n: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(n)))


def score_target(metadata: Dict) -> Dict:
    # metadata keys expected: graphql, api_count, saas_prob, b2b, admin, export, multi_tenant, auth_heavy, static
    score = 0
    complexity = 0
    roi = 0
    noise = 0

    if metadata.get("graphql"):
        score += 20
        complexity += 10
        roi += 15

    api_count = int(metadata.get("api_count") or 0)
    score += min(api_count * 6, 30)  # up to 30
    complexity += min(api_count * 4, 30)
    roi += min(api_count * 5, 30)

    saas = float(metadata.get("saas_prob") or 0.0)
    if saas > 0.5:
        score += 25
        complexity += 10
        roi += 20

    if metadata.get("b2b"):
        score += 15
        roi += 10

    if metadata.get("admin"):
        score += 15
        complexity += 10
        roi += 10

    if metadata.get("export"):
        score += 10
        roi += 8

    if metadata.get("multi_tenant"):
        score += 20
        complexity += 20
        roi += 20

    if metadata.get("auth_heavy"):
        complexity += 15
        roi += 10

    if metadata.get("static"):
        noise += 40
        score -= 30

    # New Target Intelligence Heuristics
    freshness = clamp(metadata.get("freshness", 75.0))
    
    # Reward Score: Neutral when data is missing
    reward = 50.0
    reward_confidence = 0.0
    
    # Attack Surface
    wildcard = metadata.get("wildcard", False)
    attack_surface = clamp((api_count * 10) + (30 if wildcard else 0) + (10 if metadata.get("graphql") else 0))
    
    # Competition Score
    source = str(metadata.get("source", "")).lower()
    competition = 50.0
    if source in ["hackerone", "bugcrowd"]:
        competition = 85.0
    elif source in ["intigriti"]:
        competition = 60.0
    elif source in ["yeswehack"]:
        competition = 40.0
    else:
        competition = 30.0 # private/independent
        
    # Evidence Potential (placeholder for future phases)
    evidence_potential = 0.0
    
    # Opportunity Score
    opp = 50.0 + (freshness * 0.5) - (competition * 0.8) + (attack_surface * 0.6) - (noise * 0.5) + (reward * 0.2)
    opportunity_score = clamp(opp)

    return {
        "quality_score": int(clamp(score)),
        "complexity_score": int(clamp(complexity)),
        "roi_score": int(clamp(roi)),
        "noise_level": int(clamp(noise)),
        "freshness_score": freshness,
        "competition_score": competition,
        "opportunity_score": opportunity_score,
        "reward_score": reward,
        "reward_confidence": reward_confidence,
        "attack_surface_score": attack_surface,
        "evidence_potential_score": evidence_potential
    }
