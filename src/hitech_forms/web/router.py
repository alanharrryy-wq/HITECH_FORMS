from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from hitech_forms.app.dependencies import admin_guard, get_form_service, get_submission_service
from hitech_forms.platform.errors import bad_request
from hitech_forms.services import FormService, SubmissionService

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
web_router = APIRouter()


def _query_token(request: Request) -> str:
    return str(request.query_params.get("token", "")).strip()


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=303)


@web_router.get("/admin/forms", response_class=HTMLResponse, dependencies=[Depends(admin_guard)])
def admin_forms_page(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    form_service: FormService = Depends(get_form_service),
):
    token = _query_token(request)
    result = form_service.query_list_forms(page=page, page_size=page_size)
    return templates.TemplateResponse(
        request,
        "admin_forms_list.html",
        {
            "token": token,
            "forms": result["items"],
            "page": result["page"],
            "page_size": result["page_size"],
            "has_next": result["has_next"],
            "total": result["total"],
        },
    )


@web_router.get("/admin/forms/new", response_class=HTMLResponse, dependencies=[Depends(admin_guard)])
def admin_new_form_page(request: Request):
    token = _query_token(request)
    return templates.TemplateResponse(
        request,
        "admin_form_create.html",
        {
            "token": token,
            "error": "",
            "title_value": "",
            "slug_value": "",
        },
    )


@web_router.post("/admin/forms/new", dependencies=[Depends(admin_guard)])
def admin_create_form_action(
    request: Request,
    title: str = Form(...),
    slug: str = Form(""),
    token: str = Form(""),
    form_service: FormService = Depends(get_form_service),
):
    title_value = title.strip()
    slug_value = slug.strip()
    try:
        created = form_service.command_create_form(title=title_value, slug=slug_value or None)
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "admin_form_create.html",
            {
                "token": token,
                "error": str(exc),
                "title_value": title_value,
                "slug_value": slug_value,
            },
            status_code=400,
        )
    return _redirect(f"/admin/forms/{created['id']}/fields?token={token}")


@web_router.get(
    "/admin/forms/{form_id}/fields",
    response_class=HTMLResponse,
    dependencies=[Depends(admin_guard)],
)
def admin_fields_page(
    request: Request,
    form_id: int,
    form_service: FormService = Depends(get_form_service),
):
    token = _query_token(request)
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
        "admin_field_editor.html",
        {
            "token": token,
            "form": form_detail,
            "fields_json": default_json,
            "error": "",
        },
    )


@web_router.post("/admin/forms/{form_id}/edit", dependencies=[Depends(admin_guard)])
def admin_edit_form_action(
    form_id: int,
    title: str = Form(...),
    slug: str = Form(""),
    token: str = Form(""),
    form_service: FormService = Depends(get_form_service),
):
    form_service.command_update_form(form_id=form_id, title=title, slug=slug or None)
    return _redirect(f"/admin/forms/{form_id}/fields?token={token}")


@web_router.post("/admin/forms/{form_id}/fields", dependencies=[Depends(admin_guard)])
def admin_replace_fields_action(
    form_id: int,
    fields_json: str = Form(...),
    token: str = Form(""),
    form_service: FormService = Depends(get_form_service),
):
    try:
        payload = json.loads(fields_json)
        if not isinstance(payload, list):
            raise bad_request("fields_json must be a list")
    except json.JSONDecodeError as exc:
        raise bad_request("fields_json must be valid JSON") from exc
    form_service.command_replace_fields(form_id=form_id, fields=payload)
    return _redirect(f"/admin/forms/{form_id}/fields?token={token}")


@web_router.post("/admin/forms/{form_id}/publish", dependencies=[Depends(admin_guard)])
def admin_publish_form_action(
    form_id: int,
    token: str = Form(""),
    form_service: FormService = Depends(get_form_service),
):
    form_service.command_publish_form(form_id=form_id)
    detail = form_service.query_form_detail(form_id)
    return _redirect(f"/f/{detail['slug']}?token={token}")


@web_router.post("/admin/forms/{form_id}/delete", dependencies=[Depends(admin_guard)])
def admin_delete_form_action(
    form_id: int,
    token: str = Form(""),
    form_service: FormService = Depends(get_form_service),
):
    form_service.command_delete_form(form_id)
    return _redirect(f"/admin/forms?token={token}")


@web_router.get(
    "/admin/forms/{form_id}/submissions",
    response_class=HTMLResponse,
    dependencies=[Depends(admin_guard)],
)
def admin_submissions_page(
    request: Request,
    form_id: int,
    page: int = 1,
    page_size: int = 20,
    form_service: FormService = Depends(get_form_service),
    submission_service: SubmissionService = Depends(get_submission_service),
):
    token = _query_token(request)
    detail = form_service.query_form_detail(form_id)
    submissions = submission_service.query_list_submissions(form_id=form_id, page=page, page_size=page_size)
    return templates.TemplateResponse(
        request,
        "admin_submissions_list.html",
        {
            "token": token,
            "form": detail,
            "submissions": submissions["items"],
            "page": submissions["page"],
            "has_next": submissions["has_next"],
        },
    )


@web_router.get(
    "/admin/forms/{form_id}/submissions/{submission_id}",
    response_class=HTMLResponse,
    dependencies=[Depends(admin_guard)],
)
def admin_submission_detail_page(
    request: Request,
    form_id: int,
    submission_id: int,
    form_service: FormService = Depends(get_form_service),
    submission_service: SubmissionService = Depends(get_submission_service),
):
    effective_token = _query_token(request)
    detail = form_service.query_form_detail(form_id)
    submission = submission_service.query_submission_detail(form_id=form_id, submission_id=submission_id)
    return templates.TemplateResponse(
        request,
        "admin_submission_detail.html",
        {
            "token": effective_token,
            "form": detail,
            "submission": submission,
        },
    )


@web_router.get("/f/{slug}", response_class=HTMLResponse)
def public_form_page(request: Request, slug: str, form_service: FormService = Depends(get_form_service)):
    form_detail = form_service.query_public_form(slug)
    return templates.TemplateResponse(
        request,
        "public_form.html",
        {"form": form_detail, "error": "", "submitted": False},
    )


@web_router.post("/f/{slug}/submit")
async def public_submit_form_action(
    request: Request,
    slug: str,
    form_service: FormService = Depends(get_form_service),
    submission_service: SubmissionService = Depends(get_submission_service),
):
    raw_form = await request.form()
    values = {str(key): str(value) for key, value in raw_form.multi_items()}
    try:
        submission_service.command_submit_public(slug=slug, values=values)
    except Exception as exc:
        form_detail = form_service.query_public_form(slug)
        return templates.TemplateResponse(
            request,
            "public_form.html",
            {"form": form_detail, "error": str(exc), "submitted": False},
            status_code=400,
        )
    return _redirect(f"/f/{slug}/success")


@web_router.get("/f/{slug}/success", response_class=HTMLResponse)
def public_success_page(request: Request, slug: str):
    return templates.TemplateResponse(request, "public_success.html", {"slug": slug})
