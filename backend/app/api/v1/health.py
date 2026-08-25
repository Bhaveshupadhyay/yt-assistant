"""Health check router for verifying system readiness and upstream services."""

from fastapi import APIRouter, Depends, status
from app.core.dependencies import get_health_service
from app.schemas.health import HealthResponse
from app.services.health_service import HealthService

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System health and dependency liveness",
)
async def check_health(
    health_service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    """Check database connection and Ollama daemon accessibility."""
    return await health_service.check_health()
