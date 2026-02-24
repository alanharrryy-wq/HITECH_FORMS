from __future__ import annotations

from contextlib import asynccontextmanager

from hitech_forms.platform.determinism import ensure_determinism_env
from hitech_forms.platform.logging import configure_logging
from hitech_forms.platform.settings import get_settings


@asynccontextmanager
async def lifespan(app):
    settings = get_settings()
    configure_logging(settings.log_level)
    ensure_determinism_env()
    yield
