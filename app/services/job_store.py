"""
Job store backed by Redis. Stores the status and result of async OCR jobs
as JSON under the key `ocr_job:{job_id}` with a TTL, so Redis doesn't grow
indefinitely with stale results.

Used both from FastAPI (create job / read status)
and from the Celery worker (update status as processing progresses).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import redis

from app.core.config import get_settings
from app.schemas.ocr import JobStatus

logger = logging.getLogger(__name__)

JOB_TTL_SECONDS = 60 * 60 * 24  # job results live in Redis for 24 hours
_KEY_PREFIX = "ocr_job:"


def _client() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _key(job_id: str) -> str:
    return f"{_KEY_PREFIX}{job_id}"


def create_job(job_id: str, filename: str, languages: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "job_id": job_id,
        "status": JobStatus.pending.value,
        "filename": filename,
        "languages": languages,
        "pages": None,
        "total_pages": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }
    _client().set(_key(job_id), json.dumps(record), ex=JOB_TTL_SECONDS)
    return record


def update_job(job_id: str, **fields: Any) -> Optional[dict[str, Any]]:
    client = _client()
    raw = client.get(_key(job_id))
    if raw is None:
        logger.warning("Tried to update missing job %s", job_id)
        return None

    record = json.loads(raw)
    record.update(fields)
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    client.set(_key(job_id), json.dumps(record), ex=JOB_TTL_SECONDS)
    return record


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    raw = _client().get(_key(job_id))
    if raw is None:
        return None
    return json.loads(raw)


def is_redis_available() -> bool:
    try:
        _client().ping()
        return True
    except Exception:  # noqa: BLE001
        return False
