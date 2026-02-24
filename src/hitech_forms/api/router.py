from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from hitech_forms.app.dependencies import (
    admin_guard,
    get_export_service,
    get_form_service,
    get_submission_service,
)
from hitech_forms.app.responses import canonical_json_response
from hitech_forms.services import ExportService, FormService, SubmissionService

api_router = APIRouter(prefix="/api")


class CreateFormRequest(BaseModel):
    title: str
    slug: str | None = None


class UpdateFormRequest(BaseModel):
    title: str
    slug: str | None = None


class FieldInput(BaseModel):
    key: str
    label: str
    type: str
    required: bool = False
    options: list[str] = Field(default_factory=list)


class ReplaceFieldsRequest(BaseModel):
    fields: list[FieldInput]


class SubmitFormRequest(BaseModel):
    values: dict[str, str]


@api_router.get("/health")
def health():
    payload = {"ok": True, "service": "HITECH_FORMS"}
    return canonical_json_response(payload)


@api_router.get("/admin/forms", dependencies=[Depends(admin_guard)])
def admin_list_forms(
    page: int = 1,
    page_size: int = 20,
    form_service: FormService = Depends(get_form_service),
):
    return canonical_json_response(form_service.query_list_forms(page=page, page_size=page_size))


@api_router.post("/admin/forms", dependencies=[Depends(admin_guard)])
def admin_create_form(payload: CreateFormRequest, form_service: FormService = Depends(get_form_service)):
    created = form_service.command_create_form(title=payload.title, slug=payload.slug)
    return canonical_json_response(created, status_code=201)


@api_router.get("/admin/forms/{form_id}", dependencies=[Depends(admin_guard)])
def admin_get_form(form_id: int, form_service: FormService = Depends(get_form_service)):
    return canonical_json_response(form_service.query_form_detail(form_id))


@api_router.put("/admin/forms/{form_id}", dependencies=[Depends(admin_guard)])
def admin_update_form(
    form_id: int,
    payload: UpdateFormRequest,
    form_service: FormService = Depends(get_form_service),
):
    updated = form_service.command_update_form(form_id=form_id, title=payload.title, slug=payload.slug)
    return canonical_json_response(updated)


@api_router.delete("/admin/forms/{form_id}", dependencies=[Depends(admin_guard)])
def admin_delete_form(form_id: int, form_service: FormService = Depends(get_form_service)):
    form_service.command_delete_form(form_id)
    return canonical_json_response({"ok": True})


@api_router.put("/admin/forms/{form_id}/fields", dependencies=[Depends(admin_guard)])
def admin_replace_fields(
    form_id: int,
    payload: ReplaceFieldsRequest,
    form_service: FormService = Depends(get_form_service),
):
    normalized = [item.model_dump() for item in payload.fields]
    updated = form_service.command_replace_fields(form_id=form_id, fields=normalized)
    return canonical_json_response(updated)


@api_router.post("/admin/forms/{form_id}/publish", dependencies=[Depends(admin_guard)])
def admin_publish_form(form_id: int, form_service: FormService = Depends(get_form_service)):
    published = form_service.command_publish_form(form_id)
    return canonical_json_response(published)


@api_router.get("/admin/forms/{form_id}/submissions", dependencies=[Depends(admin_guard)])
def admin_list_submissions(
    form_id: int,
    page: int = 1,
    page_size: int = 20,
    submission_service: SubmissionService = Depends(get_submission_service),
):
    return canonical_json_response(
        submission_service.query_list_submissions(form_id=form_id, page=page, page_size=page_size)
    )


@api_router.get("/admin/forms/{form_id}/submissions/{submission_id}", dependencies=[Depends(admin_guard)])
def admin_get_submission(
    form_id: int,
    submission_id: int,
    submission_service: SubmissionService = Depends(get_submission_service),
):
    return canonical_json_response(
        submission_service.query_submission_detail(form_id=form_id, submission_id=submission_id)
    )


@api_router.get("/admin/forms/{form_id}/export.csv", dependencies=[Depends(admin_guard)])
def admin_export_csv(
    form_id: int,
    version: str = "v1",
    export_service: ExportService = Depends(get_export_service),
):
    stream = export_service.stream_form_csv(form_id=form_id, export_version=version)
    headers = {"Content-Disposition": f'attachment; filename="form_{form_id}.csv"'}
    return StreamingResponse(stream, media_type="text/csv; charset=utf-8", headers=headers)


@api_router.get("/f/{slug}")
def public_get_form(slug: str, form_service: FormService = Depends(get_form_service)):
    return canonical_json_response(form_service.query_public_form(slug))


@api_router.post("/f/{slug}/submit")
def public_submit_form(
    slug: str,
    payload: SubmitFormRequest,
    submission_service: SubmissionService = Depends(get_submission_service),
):
    created: dict[str, Any] = submission_service.command_submit_public(slug=slug, values=payload.values)
    # Canonical serialization keeps response order deterministic for snapshot tests.
    return canonical_json_response(created, status_code=201)
