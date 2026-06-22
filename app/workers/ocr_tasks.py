"""Background Celery task: reads the file, runs it through ocr_service,
writes the result to job_store (Redis). The file is passed as a base64 string
in the task arguments — simpler than setting up a shared volume or object storage
between the API and the worker for a demo project."""
import base64
import logging

from app.schemas.ocr import JobStatus
from app.services import job_store, ocr_service
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="ocr.process_file", bind=True, max_retries=1)
def process_file_task(self, job_id: str, file_b64: str, content_type: str, languages: str) -> None:
    job_store.update_job(job_id, status=JobStatus.processing.value)

    try:
        file_bytes = base64.b64decode(file_b64)

        if content_type == "application/pdf":
            result = ocr_service.extract_text_from_pdf(file_bytes, languages)
        else:
            result = ocr_service.extract_text_from_image(file_bytes, languages)

        job_store.update_job(
            job_id,
            status=JobStatus.completed.value,
            pages=[page.model_dump() for page in result.pages],
            total_pages=result.total_pages,
        )
        logger.info("Job %s completed: %d page(s)", job_id, result.total_pages)

    except Exception as exc:  # noqa: BLE001 - any error must go into the job status, not crash the worker
        logger.exception("Job %s failed", job_id)
        job_store.update_job(job_id, status=JobStatus.failed.value, error=str(exc))
