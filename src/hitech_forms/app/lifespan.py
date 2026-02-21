from __future__ import annotations

from contextlib import asynccontextmanager

from hitech_forms.platform.settings import get_settings


@asynccontextmanager
async def lifespan(app):
    _ = get_settings()
    yield
