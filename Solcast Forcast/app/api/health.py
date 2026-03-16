"""
Health check API endpoint.
"""
from datetime import datetime
from fastapi import APIRouter

from app.models.response_models import HealthResponse
from app.utils.config import settings

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check if the service is running. Returns instantly without any ThingsBoard calls.",
    tags=["Health"]
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint for monitoring systems.
    
    Returns:
        HealthResponse with service status and timestamp
    """
    return HealthResponse(
        status="ok",
        service=settings.APP_NAME,
        timestamp=datetime.now()
    )
