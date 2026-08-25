"""Models router for listing active model, catalog, and verified operational models."""

from fastapi import APIRouter, Depends, status
from app.core.dependencies import get_model_service
from app.schemas.models import AvailableWorkingModelsResponse, ModelsResponse
from app.services.model_service import ModelService

router = APIRouter(prefix="/models", tags=["Models"])


@router.get(
    "",
    response_model=ModelsResponse,
    status_code=status.HTTP_200_OK,
    summary="List active model and toggleable model catalog",
)
async def list_models(
    model_service: ModelService = Depends(get_model_service),
) -> ModelsResponse:
    """Retrieve the currently active model, supported model list, and provider connectivity."""
    return await model_service.list_models()


@router.get(
    "/available",
    response_model=AvailableWorkingModelsResponse,
    status_code=status.HTTP_200_OK,
    summary="List all verified operational and working models",
)
@router.get(
    "/working",
    response_model=AvailableWorkingModelsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_available_working_models(
    model_service: ModelService = Depends(get_model_service),
) -> AvailableWorkingModelsResponse:
    """Actively verify live connectivity and return all currently working models across providers."""
    return await model_service.get_available_working_models()
