import fakeredis
import pytest

from app.services import job_store


@pytest.fixture(autouse=True)
def patch_redis_client(monkeypatch):
    """Replace the real Redis client with fakeredis for all tests in this file,
    so no running Redis server is required locally or in CI."""
    fake_client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(job_store, "_client", lambda: fake_client)
    return fake_client


def test_create_and_get_job():
    record = job_store.create_job("job-1", "file.png", "eng")
    assert record["status"] == "pending"

    fetched = job_store.get_job("job-1")
    assert fetched["job_id"] == "job-1"
    assert fetched["filename"] == "file.png"


def test_update_job_changes_status_and_fields():
    job_store.create_job("job-2", "file.pdf", "eng+rus")
    updated = job_store.update_job("job-2", status="completed", total_pages=3)

    assert updated["status"] == "completed"
    assert updated["total_pages"] == 3

    fetched = job_store.get_job("job-2")
    assert fetched["status"] == "completed"


def test_update_missing_job_returns_none():
    result = job_store.update_job("does-not-exist", status="completed")
    assert result is None


def test_get_missing_job_returns_none():
    assert job_store.get_job("does-not-exist") is None
