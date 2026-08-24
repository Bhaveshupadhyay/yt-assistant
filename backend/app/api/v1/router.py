"""API v1 consolidated router."""

from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.sessions import router as sessions_router

api_v1_router = APIRouter()

# Register endpoint sub-routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(sessions_router)
