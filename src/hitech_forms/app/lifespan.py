from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager

from hitech_forms.platform.determinism import ensure_determinism_env
from hitech_forms.platform.logging import configure_logging, get_logger, log_event
from hitech_forms.platform.request_context import reset_request_context, set_startup_seed
from hitech_forms.platform.settings import get_settings


@asynccontextmanager
async def lifespan(app):
    settings = get_settings()
    configure_logging(settings.log_level)
    ensure_determinism_env()
    seed_source = f"{settings.db_path}|{settings.host}|{settings.port}"
    startup_seed = hashlib.sha256(seed_source.encode("utf-8")).hexdigest()[:12]
    set_startup_seed(startup_seed)
    reset_request_context()
    log_event(get_logger("hitech_forms.app"), "app_started", startup_seed=startup_seed)
    yield
