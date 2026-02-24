from __future__ import annotations

from fastapi import APIRouter

from hitech_forms.app.responses import canonical_json_response


def build_health_router() -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health():
        payload = {"ok": True, "service": "HITECH_FORMS"}
        return canonical_json_response(payload)

    return router
