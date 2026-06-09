from fastapi import APIRouter

from api.schemas.models import ReportOut
from api.services.data_service import generate_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/generate", response_model=ReportOut)
def get_report():
    return generate_report()
