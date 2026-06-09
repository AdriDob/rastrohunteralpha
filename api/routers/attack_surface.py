from fastapi import APIRouter

from api.schemas.models import AttackSurfaceGroup
from api.services.data_service import get_attack_surfaces

router = APIRouter(prefix="/api/attack-surface", tags=["attack-surface"])


@router.get("", response_model=dict[str, list])
def get_surfaces():
    return get_attack_surfaces()
