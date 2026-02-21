from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

web_router = APIRouter()


@web_router.get("/admin/forms")
def admin_forms():
    return HTMLResponse(
        "<html><body><h1>HITECH_FORMS</h1><p>Wave 1: SSR skeleton ✅</p></body></html>"
    )
