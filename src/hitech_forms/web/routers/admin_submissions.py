from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from hitech_forms.app.dependencies import admin_guard, get_form_service, get_submission_service
from hitech_forms.contracts import FormServicePort, SubmissionServicePort
from hitech_forms.web.routers.common import query_token, templates


def build_admin_submissions_web_router() -> APIRouter:
    router = APIRouter(prefix="/admin/forms", dependencies=[Depends(admin_guard)])

    @router.get("/{form_id}/submissions", response_class=HTMLResponse)
    def admin_submissions_page(
        request: Request,
        form_id: int,
        page: int = 1,
        page_size: int = 20,
        form_service: FormServicePort = Depends(get_form_service),
        submission_service: SubmissionServicePort = Depends(get_submission_service),
    ):
        token = query_token(request)
        detail = form_service.query_form_detail(form_id)
        submissions = submission_service.query_list_submissions(form_id=form_id, page=page, page_size=page_size)
        return templates.TemplateResponse(
            request,
            "admin/submissions/list.html",
            {
                "token": token,
                "form": detail,
                "submissions": submissions["items"],
                "page": submissions["page"],
                "has_next": submissions["has_next"],
            },
        )

    @router.get("/{form_id}/submissions/{submission_id}", response_class=HTMLResponse)
    def admin_submission_detail_page(
        request: Request,
        form_id: int,
        submission_id: int,
        form_service: FormServicePort = Depends(get_form_service),
        submission_service: SubmissionServicePort = Depends(get_submission_service),
    ):
        token = query_token(request)
        detail = form_service.query_form_detail(form_id)
        submission = submission_service.query_submission_detail(form_id=form_id, submission_id=submission_id)
        return templates.TemplateResponse(
            request,
            "admin/submissions/detail.html",
            {
                "token": token,
                "form": detail,
                "submission": submission,
            },
        )

    return router
