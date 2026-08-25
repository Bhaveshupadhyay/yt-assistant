"""Service for checking system readiness, database connectivity, and daemon liveness."""

from datetime import datetime, timezone
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.clients import get_ollama_client
from app.core.config import Settings, get_settings
from app.core.enums import HealthStatus
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)


class HealthService:
    """Service handling health checks for database and local Ollama daemon."""

    def __init__(
        self,
        db: AsyncSession,
        settings: Settings | None = None,
    ) -> None:
        """Initialize HealthService.

        Args:
            db: Active asynchronous database session.
            settings: Optional application settings.
        """
        self.db = db
        self.settings = settings or get_settings()

    async def check_health(self) -> HealthResponse:
        """Execute connectivity probes and aggregate overall system health status.

        Returns:
            HealthResponse: Combined database, Ollama, and overall health status.
        """
        # 1. Database Check
        db_healthy = False
        try:
            result = await self.db.execute(text("SELECT 1"))
            db_healthy = bool(result.scalar() == 1)
        except Exception as exc:
            logger.warning(f"Database health check failed: {exc}")

        # 2. Ollama Check (centralized client with non-blocking short timeout)
        ollama_healthy = False
        try:
            ollama_client = get_ollama_client(self.settings)
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
            version=self.settings.APP_VERSION,
        )
