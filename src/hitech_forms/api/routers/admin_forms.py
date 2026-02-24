from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from hitech_forms.app.dependencies import admin_guard, get_form_service
from hitech_forms.app.responses import canonical_json_response
from hitech_forms.contracts import FormServicePort


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


def build_admin_forms_router() -> APIRouter:
    router = APIRouter(prefix="/admin/forms", dependencies=[Depends(admin_guard)])

    @router.get("")
    def admin_list_forms(
        page: int = 1,
        page_size: int = 20,
        form_service: FormServicePort = Depends(get_form_service),
    ):
        return canonical_json_response(form_service.query_list_forms(page=page, page_size=page_size))

    @router.post("")
    def admin_create_form(
        payload: CreateFormRequest,
        form_service: FormServicePort = Depends(get_form_service),
    ):
        created = form_service.command_create_form(title=payload.title, slug=payload.slug)
        return canonical_json_response(created, status_code=201)

    @router.get("/{form_id}")
    def admin_get_form(form_id: int, form_service: FormServicePort = Depends(get_form_service)):
        return canonical_json_response(form_service.query_form_detail(form_id))

    @router.put("/{form_id}")
    def admin_update_form(
        form_id: int,
        payload: UpdateFormRequest,
        form_service: FormServicePort = Depends(get_form_service),
    ):
        updated = form_service.command_update_form(form_id=form_id, title=payload.title, slug=payload.slug)
        return canonical_json_response(updated)

    @router.delete("/{form_id}")
    def admin_delete_form(form_id: int, form_service: FormServicePort = Depends(get_form_service)):
        form_service.command_delete_form(form_id)
        return canonical_json_response({"ok": True})

    @router.put("/{form_id}/fields")
    def admin_replace_fields(
        form_id: int,
        payload: ReplaceFieldsRequest,
        form_service: FormServicePort = Depends(get_form_service),
    ):
        normalized = [item.model_dump() for item in payload.fields]
        updated = form_service.command_replace_fields(form_id=form_id, fields=normalized)
        return canonical_json_response(updated)

    @router.post("/{form_id}/publish")
    def admin_publish_form(form_id: int, form_service: FormServicePort = Depends(get_form_service)):
        published = form_service.command_publish_form(form_id)
        return canonical_json_response(published)

    return router
