"""
Application entry point:
- assembles the FastAPI app and mounts routers under /api/v1
- registers global error handlers (domain exceptions → clean JSON)
- attaches rate limiting via slowapi
- configures logging on startup
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.exceptions import OCRGatewayError
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.routers import health, ocr

settings = get_settings()
setup_logging(debug=settings.debug)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s starting in '%s' environment", settings.app_name, settings.environment)
    yield
    logger.info("%s shutting down", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description=(
        "REST API for OCR text extraction from images and PDFs using Tesseract. "
        "Supports synchronous and asynchronous (queue-based) processing modes."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # open for demo; restrict to specific domains in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(OCRGatewayError)
async def ocr_gateway_exception_handler(request: Request, exc: OCRGatewayError) -> JSONResponse:
    """Convert domain exceptions to clean JSON instead of an HTML 500 page."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(health.router, prefix="/api/v1")
app.include_router(ocr.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"service": settings.app_name, "docs": "/docs", "health": "/api/v1/health"}
