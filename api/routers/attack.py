from typing import Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/attack", tags=["attack"])


@router.get("/decision")
def attack_decision(
    target_id: Optional[int] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
):
    from database import db, models
    from core.attack import AttackDecisionEngine

    engine = AttackDecisionEngine()
    session = db.SessionLocal()
    try:
        query = session.query(models.Endpoint)
        if target_id is not None:
            query = query.filter(models.Endpoint.target_id == target_id)
        endpoints = query.limit(limit).all()

        if not endpoints:
            return {"message": "No endpoints available for evaluation."}

        endpoint_data = []
        for ep in endpoints:
            endpoint_data.append({
                "path": ep.path,
                "method": ep.method,
                "params": ep.parsed_params,
                "target_id": ep.target_id,
            })

        return engine.evaluate_endpoints(endpoint_data)
    finally:
        session.close()
