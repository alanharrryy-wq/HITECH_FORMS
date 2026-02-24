from __future__ import annotations

from fastapi import APIRouter

from hitech_forms.api.routers import (
    build_admin_export_router,
    build_admin_forms_router,
    build_admin_submissions_router,
    build_health_router,
    build_public_forms_router,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(build_health_router())
api_router.include_router(build_admin_forms_router())
api_router.include_router(build_admin_submissions_router())
api_router.include_router(build_admin_export_router())
api_router.include_router(build_public_forms_router())
