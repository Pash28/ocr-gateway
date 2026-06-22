from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.ocr import HealthResponse
from app.services import job_store, ocr_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Service health check")
def health_check() -> HealthResponse:
    """Used by Docker HEALTHCHECK and platforms like Render/Railway
    to confirm the container is ready to receive traffic."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
        tesseract_available=ocr_service.is_tesseract_available(),
        redis_available=job_store.is_redis_available(),
    )
