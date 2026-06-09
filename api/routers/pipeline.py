from fastapi import APIRouter

from api.schemas.models import PipelineStageOut
from api.services.data_service import get_pipeline_stages

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("", response_model=PipelineStageOut)
def get_pipeline():
    return get_pipeline_stages()
