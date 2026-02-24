from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from hitech_forms.app.dependencies import admin_guard, get_form_service
from hitech_forms.contracts import FormServicePort
from hitech_forms.platform.errors import bad_request
from hitech_forms.web.routers.common import query_token, redirect, templates


def build_admin_forms_web_router() -> APIRouter:
    router = APIRouter(prefix="/admin/forms", dependencies=[Depends(admin_guard)])

    @router.get("", response_class=HTMLResponse)
    def admin_forms_page(
        request: Request,
        page: int = 1,
        page_size: int = 10,
        form_service: FormServicePort = Depends(get_form_service),
    ):
        token = query_token(request)
        result = form_service.query_list_forms(page=page, page_size=page_size)
        return templates.TemplateResponse(
            request,
            "admin/forms/list.html",
            {
                "token": token,
                "forms": result["items"],
                "page": result["page"],
                "page_size": result["page_size"],
                "has_next": result["has_next"],
                "total": result["total"],
            },
        )

    @router.get("/new", response_class=HTMLResponse)
    def admin_new_form_page(request: Request):
        token = query_token(request)
        return templates.TemplateResponse(
            request,
            "admin/forms/create.html",
            {
                "token": token,
                "error": "",
                "title_value": "",
                "slug_value": "",
            },
        )

    @router.post("/new")
    def admin_create_form_action(
        request: Request,
        title: str = Form(...),
        slug: str = Form(""),
        token: str = Form(""),
        form_service: FormServicePort = Depends(get_form_service),
    ):
        title_value = title.strip()
        slug_value = slug.strip()
        try:
            created = form_service.command_create_form(title=title_value, slug=slug_value or None)
        except Exception as exc:
            return templates.TemplateResponse(
                request,
                "admin/forms/create.html",
                {
                    "token": token,
                    "error": str(exc),
                    "title_value": title_value,
                    "slug_value": slug_value,
                },
                status_code=400,
            )
        return redirect(f"/admin/forms/{created['id']}/fields?token={token}")

    @router.get("/{form_id}/fields", response_class=HTMLResponse)
    def admin_fields_page(
        request: Request,
        form_id: int,
        form_service: FormServicePort = Depends(get_form_service),
    ):
        token = query_token(request)
        form_detail = form_service.query_form_detail(form_id)
        default_json = json.dumps(
            [
                {
                    "key": field["key"],
                    "label": field["label"],
                    "type": field["field_type"],
                    "required": field["required"],
                    "options": field["options"],
                }
                for field in form_detail["fields"]
            ],
            indent=2,
        )
        return templates.TemplateResponse(
            request,
            "admin/forms/field_editor.html",
            {
                "token": token,
                "form": form_detail,
                "fields_json": default_json,
                "error": "",
            },
        )

    @router.post("/{form_id}/edit")
    def admin_edit_form_action(
        form_id: int,
        title: str = Form(...),
        slug: str = Form(""),
        token: str = Form(""),
        form_service: FormServicePort = Depends(get_form_service),
    ):
        form_service.command_update_form(form_id=form_id, title=title, slug=slug or None)
        return redirect(f"/admin/forms/{form_id}/fields?token={token}")

    @router.post("/{form_id}/fields")
    def admin_replace_fields_action(
        form_id: int,
        fields_json: str = Form(...),
        token: str = Form(""),
        form_service: FormServicePort = Depends(get_form_service),
    ):
        try:
            payload = json.loads(fields_json)
            if not isinstance(payload, list):
                raise bad_request("fields_json must be a list")
        except json.JSONDecodeError as exc:
            raise bad_request("fields_json must be valid JSON") from exc
        form_service.command_replace_fields(form_id=form_id, fields=payload)
        return redirect(f"/admin/forms/{form_id}/fields?token={token}")

    @router.post("/{form_id}/publish")
    def admin_publish_form_action(
        form_id: int,
        token: str = Form(""),
        form_service: FormServicePort = Depends(get_form_service),
    ):
        form_service.command_publish_form(form_id=form_id)
        detail = form_service.query_form_detail(form_id)
        return redirect(f"/f/{detail['slug']}?token={token}")

    @router.post("/{form_id}/delete")
    def admin_delete_form_action(
        form_id: int,
        token: str = Form(""),
        form_service: FormServicePort = Depends(get_form_service),
    ):
        form_service.command_delete_form(form_id)
        return redirect(f"/admin/forms?token={token}")

    return router
