"""Health check router for verifying system readiness and upstream services using Enums."""

from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, status
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.clients import get_ollama_client
from app.core.config import Settings, get_settings
from app.core.dependencies import get_db
from app.core.enums import HealthStatus
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System health and dependency liveness",
)
async def check_health(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Check database connection and Ollama daemon accessibility."""
    # 1. Database Check
    db_healthy = False
    try:
        result = await db.execute(text("SELECT 1"))
        db_healthy = bool(result.scalar() == 1)
    except Exception as exc:
        logger.warning(f"Database health check failed: {exc}")

    # 2. Ollama Check (centralized client with non-blocking short timeout)
    ollama_healthy = False
    try:
        ollama_client = get_ollama_client(settings)
        resp = await ollama_client.get("/api/tags", timeout=2.0)
        ollama_healthy = resp.status_code == 200
    except Exception as exc:
        logger.debug(f"Ollama health check unreachable: {exc}")

    overall_status = (
        HealthStatus.OK if (db_healthy and ollama_healthy) else HealthStatus.DEGRADED
    )

    return HealthResponse(
        status=overall_status,
        database=db_healthy,
        ollama=ollama_healthy,
        timestamp=datetime.now(timezone.utc),
        version=settings.APP_VERSION,
    )
