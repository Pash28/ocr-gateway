"""
Main OCR endpoints.

Design decision: two explicit modes instead of one "smart" endpoint —
- /sync is designed for fast responses (images, small PDFs) and returns text immediately;
- /async queues a Celery task and does not block the HTTP worker on large PDFs.

This way the API client picks the behavior explicitly rather than sometimes getting
a fast response and sometimes a 30-second hang from the same endpoint.
"""
import base64
import logging
import uuid

from fastapi import APIRouter, Depends, Request, UploadFile, File, Form

from app.core.config import Settings, get_settings
from app.core.exceptions import JobNotFoundError
from app.core.rate_limit import limiter
from app.core.security import verify_api_key
from app.core.validation import validate_and_read_upload
from app.schemas.ocr import (
    OCRJobAcceptedResponse,
    OCRJobResultResponse,
    OCRSyncResponse,
    JobStatus,
)
from app.services import job_store, ocr_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["ocr"], dependencies=[Depends(verify_api_key)])


@router.post(
    "/sync",
    response_model=OCRSyncResponse,
    summary="Synchronous OCR (image or short PDF)",
)
@limiter.limit(f"{get_settings().rate_limit_per_minute}/minute")
async def ocr_sync(
    request: Request,
    file: UploadFile = File(..., description="Image (PNG/JPEG/WebP/BMP/TIFF) or PDF"),
    languages: str = Form(default=None, description="Tesseract language code(s), e.g. 'eng' or 'eng+rus'"),
    settings: Settings = Depends(get_settings),
) -> OCRSyncResponse:
    file_bytes, content_type = await validate_and_read_upload(file, settings)
    langs = languages or settings.default_languages

    if content_type == settings.allowed_pdf_type:
        result = ocr_service.extract_text_from_pdf(
            file_bytes, langs, max_pages=settings.max_pdf_pages_sync
        )
    else:
        result = ocr_service.extract_text_from_image(file_bytes, langs)

    return OCRSyncResponse(
        filename=file.filename or "unknown",
        content_type=content_type,
        languages=langs,
        pages=result.pages,
        total_pages=result.total_pages,
        processing_time_ms=result.processing_time_ms,
    )


@router.post(
    "/async",
    response_model=OCRJobAcceptedResponse,
    status_code=202,
    summary="Queue a file for OCR processing (for large PDFs)",
)
@limiter.limit(f"{get_settings().rate_limit_per_minute}/minute")
async def ocr_async(
    request: Request,
    file: UploadFile = File(...),
    languages: str = Form(default=None),
    settings: Settings = Depends(get_settings),
) -> OCRJobAcceptedResponse:
    file_bytes, content_type = await validate_and_read_upload(file, settings)
    langs = languages or settings.default_languages

    job_id = str(uuid.uuid4())
    record = job_store.create_job(job_id, file.filename or "unknown", langs)

    # Local import so the Celery task (and its worker imports) are not pulled in
    # on every FastAPI process startup — the API process doesn't execute tasks itself.
    from app.workers.ocr_tasks import process_file_task

    file_b64 = base64.b64encode(file_bytes).decode("ascii")
    process_file_task.delay(job_id, file_b64, content_type, langs)

    logger.info("Queued OCR job %s for file '%s'", job_id, file.filename)

    return OCRJobAcceptedResponse(
        job_id=job_id,
        status=JobStatus(record["status"]),
        status_url=f"/api/v1/ocr/jobs/{job_id}",
        created_at=record["created_at"],
    )


@router.get(
    "/jobs/{job_id}",
    response_model=OCRJobResultResponse,
    summary="Get the status and result of an async job",
)
async def get_job_status(job_id: str) -> OCRJobResultResponse:
    record = job_store.get_job(job_id)
    if record is None:
        raise JobNotFoundError(job_id)

    return OCRJobResultResponse(**record)
