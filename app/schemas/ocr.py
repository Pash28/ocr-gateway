"""Pydantic schemas — the single source of truth for the API contract.
FastAPI uses these to generate OpenAPI/Swagger docs and validate data automatically."""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class PageResult(BaseModel):
    page_number: int = Field(..., description="Page number, starting from 1")
    text: str = Field(..., description="Recognized text for this page")
    mean_confidence: float = Field(..., description="Mean OCR confidence for this page, 0-100")
    word_count: int = Field(..., description="Number of recognized words")


class OCRSyncResponse(BaseModel):
    filename: str
    content_type: str
    languages: str
    pages: List[PageResult]
    total_pages: int
    processing_time_ms: float


class OCRJobAcceptedResponse(BaseModel):
    job_id: str
    status: JobStatus
    status_url: str
    created_at: datetime


class OCRJobResultResponse(BaseModel):
    job_id: str
    status: JobStatus
    filename: Optional[str] = None
    languages: Optional[str] = None
    pages: Optional[List[PageResult]] = None
    total_pages: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    tesseract_available: bool
    redis_available: bool


class ErrorResponse(BaseModel):
    detail: str
