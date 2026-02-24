from __future__ import annotations

from fastapi import APIRouter

from hitech_forms.web.routers import (
    build_admin_forms_web_router,
    build_admin_submissions_web_router,
    build_public_forms_web_router,
)

web_router = APIRouter()
web_router.include_router(build_admin_forms_web_router())
web_router.include_router(build_admin_submissions_web_router())
web_router.include_router(build_public_forms_web_router())
