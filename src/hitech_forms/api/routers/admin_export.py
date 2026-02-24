from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from hitech_forms.app.dependencies import admin_guard, get_export_service
from hitech_forms.contracts import ExportServicePort


def build_admin_export_router() -> APIRouter:
    router = APIRouter(prefix="/admin/forms", dependencies=[Depends(admin_guard)])

    @router.get("/{form_id}/export.csv")
    def admin_export_csv(
        form_id: int,
        version: str = "v1",
        export_service: ExportServicePort = Depends(get_export_service),
    ):
        stream = export_service.stream_form_csv(form_id=form_id, export_version=version)
        headers = {"Content-Disposition": f'attachment; filename="form_{form_id}.csv"'}
        return StreamingResponse(stream, media_type="text/csv; charset=utf-8", headers=headers)

    return router
