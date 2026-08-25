"""Application lifespan manager for startup and shutdown event handling."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from app.core.clients import close_all_clients, init_all_clients
from app.core.config import get_settings
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager: startup before yield, guaranteed shutdown cleanup via try...finally."""
    settings = get_settings()

    # 1. Startup: Logging, Database & Infrastructure initialization
    setup_logging(settings)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} (env: {settings.ENVIRONMENT})...")

    try:
        await init_all_clients(settings)
        yield
    finally:
        # 2. Shutdown: Guaranteed clean up of client pools and connections
        logger.info(f"Shutting down {settings.APP_NAME}...")
        await close_all_clients()
        logger.info("All infrastructure client connections closed cleanly.")
