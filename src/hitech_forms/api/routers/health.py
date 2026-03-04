from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from hitech_forms.app.responses import canonical_json_response
from hitech_forms.db import get_engine


def build_health_router() -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health():
        payload = {"ok": True, "service": "HITECH_FORMS"}
        return canonical_json_response(payload)

    @router.get("/health/db")
    def health_db():
        db_ok = False
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False
        payload = {"ok": db_ok, "service": "HITECH_FORMS", "db_ok": db_ok}
        return canonical_json_response(payload, status_code=200 if db_ok else 503)

    return router
