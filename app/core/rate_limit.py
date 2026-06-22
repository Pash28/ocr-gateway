"""Shared Limiter instance (slowapi) — extracted into its own module
to avoid circular imports between main.py and routers."""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

_settings = get_settings()

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{_settings.rate_limit_per_minute}/minute"])
