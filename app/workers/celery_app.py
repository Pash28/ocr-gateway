"""Celery initialization. Redis is used as both the broker and the result backend
to avoid pulling in an extra service in docker-compose for a demo project."""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ocr_gateway",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.ocr_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_time_limit=settings.celery_task_time_limit_seconds,
    worker_max_tasks_per_child=50,  # guard against memory leaks in long-lived workers
)
