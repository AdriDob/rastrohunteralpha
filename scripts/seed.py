"""Seed script — populate Rastro DB with demo data for development/testing.

Usage:
    source .venv/bin/activate
    python scripts/seed.py

Safe to run multiple times (idempotent via delete + insert).
"""

import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from database import db, models
from database.db import SessionLocal


DEMO_TARGETS = [
    {"name": "Airbyte", "domain": "api.airbyte.com"},
    {"name": "Linear", "domain": "app.linear.app"},
    {"name": "Uniswap", "domain": "app.uniswap.org"},
    {"name": "Segment", "domain": "api.segment.com"},
    {"name": "StarkNet", "domain": "starknet.io"},
]

DEMO_ENDPOINTS = {
    "Airbyte": [
        ("GET", "/api/v1/users/{id}", '{"risk":"medium","auth":"required"}'),
        ("GET", "/api/v1/workspaces", '{"risk":"low","auth":"required"}'),
        ("POST", "/api/v1/connections", '{"risk":"high","auth":"required"}'),
        ("GET", "/api/v1/sources", '{"risk":"medium","auth":"required"}'),
        ("GET", "/api/v1/destinations", '{"risk":"low","auth":"required"}'),
        ("POST", "/api/v1/connector_builder", '{"risk":"high","auth":"admin"}'),
        ("GET", "/api/v1/health", '{"risk":"low","auth":"none"}'),
        ("GET", "/api/v1/attempt", '{"risk":"medium","auth":"required"}'),
        ("POST", "/api/v1/jobs/cancel", '{"risk":"high","auth":"required"}'),
        ("GET", "/api/v1/operations", '{"risk":"low","auth":"required"}'),
    ],
    "Linear": [
        ("GET", "/graphql", '{"risk":"high","auth":"required"}'),
        ("POST", "/graphql", '{"risk":"critical","auth":"required"}'),
        ("GET", "/api/v1/oauth/token", '{"risk":"high","auth":"none"}'),
        ("GET", "/api/v1/users", '{"risk":"medium","auth":"required"}'),
        ("GET", "/api/v1/teams", '{"risk":"low","auth":"required"}'),
        ("POST", "/api/v1/import", '{"risk":"high","auth":"admin"}'),
        ("GET", "/api/v1/issues", '{"risk":"medium","auth":"required"}'),
        ("GET", "/api/v1/projects", '{"risk":"low","auth":"required"}'),
        ("POST", "/api/v1/attachments", '{"risk":"medium","auth":"required"}'),
        ("DELETE", "/api/v1/issues/{id}", '{"risk":"high","auth":"required"}'),
    ],
    "Uniswap": [
        ("GET", "/api/v1/quote", '{"risk":"medium","auth":"none"}'),
        ("POST", "/api/v1/swap", '{"risk":"critical","auth":"required"}'),
        ("GET", "/api/v1/pools", '{"risk":"low","auth":"none"}'),
        ("GET", "/api/v1/tokens", '{"risk":"low","auth":"none"}'),
        ("POST", "/api/v1/positions", '{"risk":"high","auth":"required"}'),
        ("GET", "/api/v1/orders", '{"risk":"medium","auth":"required"}'),
        ("GET", "/api/v1/governance/proposals", '{"risk":"low","auth":"none"}'),
        ("DELETE", "/api/v1/positions/{id}", '{"risk":"high","auth":"required"}'),
        ("GET", "/api/v1/fees", '{"risk":"medium","auth":"none"}'),
        ("POST", "/api/v1/approve", '{"risk":"high","auth":"required"}'),
    ],
    "Segment": [
        ("GET", "/api/v1/users", '{"risk":"medium","auth":"required"}'),
        ("POST", "/api/v1/import", '{"risk":"high","auth":"required"}'),
        ("GET", "/api/v1/workspaces", '{"risk":"low","auth":"required"}'),
        ("GET", "/api/v1/sources", '{"risk":"low","auth":"required"}'),
        ("POST", "/api/v1/destinations", '{"risk":"medium","auth":"required"}'),
        ("GET", "/api/v1/admin/export", '{"risk":"critical","auth":"admin"}'),
        ("PUT", "/api/v1/config", '{"risk":"high","auth":"admin"}'),
        ("GET", "/api/v1/regions", '{"risk":"low","auth":"none"}'),
        ("POST", "/api/v1/webhooks", '{"risk":"medium","auth":"required"}'),
        ("DELETE", "/api/v1/sources/{id}", '{"risk":"high","auth":"required"}'),
    ],
    "StarkNet": [
        ("GET", "/api/v1/contracts", '{"risk":"low","auth":"none"}'),
        ("POST", "/api/v1/call", '{"risk":"medium","auth":"none"}'),
        ("GET", "/api/v1/transactions", '{"risk":"low","auth":"none"}'),
        ("POST", "/api/v1/invoke", '{"risk":"critical","auth":"required"}'),
        ("GET", "/api/v1/events", '{"risk":"low","auth":"none"}'),
        ("GET", "/api/v1/blocks", '{"risk":"low","auth":"none"}'),
        ("POST", "/api/v1/deploy", '{"risk":"high","auth":"required"}'),
        ("GET", "/api/v1/state", '{"risk":"medium","auth":"none"}'),
        ("GET", "/api/v1/fees", '{"risk":"low","auth":"none"}'),
        ("GET", "/api/v1/tokens", '{"risk":"low","auth":"none"}'),
    ],
}

DEMO_FINDINGS = [
    {"target": "Airbyte", "endpoint_idx": 2, "title": "IDOR en creación de conexiones", "severity": "critical", "desc": "Se puede modificar connections de otros usuarios cambiando el ID en POST /api/v1/connections"},
    {"target": "Airbyte", "endpoint_idx": 5, "title": "Admin endpoint sin rate limiting", "severity": "high", "desc": "POST /api/v1/connector_builder no tiene rate limiting"},
    {"target": "Linear", "endpoint_idx": 0, "title": "GraphQL introspection habilitado", "severity": "high", "desc": "El schema GraphQL completo está expuesto via introspection"},
    {"target": "Linear", "endpoint_idx": 1, "title": "Mass assignment en mutations", "severity": "critical", "desc": "GraphQL mutations permiten modificar campos no autorizados"},
    {"target": "Uniswap", "endpoint_idx": 0, "title": "Quote sin autenticación expone precios", "severity": "medium", "desc": "GET /api/v1/quote no requiere auth pero expone datos sensibles"},
    {"target": "Uniswap", "endpoint_idx": 9, "title": "Falta de validación en approve", "severity": "high", "desc": "POST /api/v1/approve no valida correctamente el spender"},
    {"target": "Segment", "endpoint_idx": 6, "title": "Export admin sin autenticación fuerte", "severity": "high", "desc": "GET /api/v1/admin/export accesible con token de usuario normal"},
    {"target": "StarkNet", "endpoint_idx": 3, "title": "Invoke sin límite de gas", "severity": "medium", "desc": "POST /api/v1/invoke no valida límite de gas mínimo"},
]


def main():
    db.init_db()
    session = SessionLocal()

    # Re-seed: clean old data
    try:
        from core_engines.targets.models import TargetIntel
        session.query(TargetIntel).delete()
    except Exception:
        pass
    session.query(models.Finding).delete()
    session.query(models.Endpoint).delete()
    session.query(models.Target).delete()
    session.commit()
    print("Existing data cleared.")

    # Create targets
    target_map = {}
    for td in DEMO_TARGETS:
        t = models.Target(name=td["name"], domain=td["domain"])
        session.add(t)
        session.flush()
        target_map[td["name"]] = t
        print(f"  + Target: {td['name']} ({td['domain']})")

    # Create endpoints
    ep_map = {}
    for tname, endpoints in DEMO_ENDPOINTS.items():
        target = target_map[tname]
        for method, path, params in endpoints:
            ep = models.Endpoint(
                target_id=target.id,
                path=path,
                method=method,
                params=params,
            )
            session.add(ep)
            session.flush()
            ep_map[(tname, path)] = ep
    print(f"  + Endpoints: {sum(len(v) for v in DEMO_ENDPOINTS.values())}")

    # Create findings
    for fd in DEMO_FINDINGS:
        target = target_map[fd["target"]]
        endpoint = ep_map.get((fd["target"], DEMO_ENDPOINTS[fd["target"]][fd["endpoint_idx"]][1]))
        f = models.Finding(
            target_id=target.id,
            endpoint_id=endpoint.id if endpoint else None,
            title=fd["title"],
            severity=fd["severity"],
            description=fd["desc"],
        )
        session.add(f)
    print(f"  + Findings: {len(DEMO_FINDINGS)}")

    # Seed targets_intel
    intel_data = [
        {"target": "Airbyte", "reward_score": 85, "opportunity_score": 78, "competition_score": 65, "freshness_score": 90, "attack_surface_score": 72, "evidence_potential_score": 80},
        {"target": "Linear", "reward_score": 92, "opportunity_score": 88, "competition_score": 55, "freshness_score": 70, "attack_surface_score": 85, "evidence_potential_score": 90},
        {"target": "Uniswap", "reward_score": 95, "opportunity_score": 92, "competition_score": 80, "freshness_score": 60, "attack_surface_score": 60, "evidence_potential_score": 75},
        {"target": "Segment", "reward_score": 70, "opportunity_score": 75, "competition_score": 50, "freshness_score": 85, "attack_surface_score": 78, "evidence_potential_score": 70},
        {"target": "StarkNet", "reward_score": 88, "opportunity_score": 82, "competition_score": 45, "freshness_score": 95, "attack_surface_score": 45, "evidence_potential_score": 65},
    ]
    try:
        from core_engines.targets.models import TargetIntel
        for idata in intel_data:
            target = target_map[idata["target"]]
            existing = session.query(TargetIntel).filter(TargetIntel.id == target.id).first()
            if not existing:
                ti = TargetIntel(id=target.id)
                ti.reward_score = idata["reward_score"]
                ti.opportunity_score = idata["opportunity_score"]
                ti.competition_score = idata["competition_score"]
                ti.freshness_score = idata["freshness_score"]
                ti.attack_surface_score = idata["attack_surface_score"]
                ti.evidence_potential_score = idata["evidence_potential_score"]
                session.add(ti)
        print(f"  + targets_intel: {len(intel_data)}")
    except Exception as e:
        print(f"  ~ targets_intel skipped ({e})")

    session.commit()
    session.close()
    print(f"\nSeed completo! {len(DEMO_TARGETS)} targets, endpoints, findings, intel.")


if __name__ == "__main__":
    main()
