from fastapi import APIRouter

from api.services.data_service import get_digest

router = APIRouter(prefix="/api/digest", tags=["digest"])


@router.get("")
def digest():
    return get_digest()
