"""Simple but production-grade authentication via X-API-Key header.

For a real production system this can be extended to verify keys from a database
with per-tier rate limits — the extension point is already in place.
"""
from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()

    if not settings.api_key_enabled:
        return

    if x_api_key is None or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Provide it via the 'X-API-Key' header.",
        )
