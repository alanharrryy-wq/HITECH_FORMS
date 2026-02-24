from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from hitech_forms.app.dependencies import get_form_service, get_submission_service
from hitech_forms.contracts import FormServicePort, SubmissionServicePort
from hitech_forms.web.routers.common import redirect, templates


def build_public_forms_web_router() -> APIRouter:
    router = APIRouter(prefix="/f")

    @router.get("/{slug}", response_class=HTMLResponse)
    def public_form_page(request: Request, slug: str, form_service: FormServicePort = Depends(get_form_service)):
        form_detail = form_service.query_public_form(slug)
        return templates.TemplateResponse(
            request,
            "public/form.html",
            {"form": form_detail, "error": "", "submitted": False},
        )

    @router.post("/{slug}/submit")
    async def public_submit_form_action(
        request: Request,
        slug: str,
        form_service: FormServicePort = Depends(get_form_service),
        submission_service: SubmissionServicePort = Depends(get_submission_service),
    ):
        raw_form = await request.form()
        values = {str(key): str(value) for key, value in raw_form.multi_items()}
        try:
            submission_service.command_submit_public(slug=slug, values=values)
        except Exception as exc:
            form_detail = form_service.query_public_form(slug)
            return templates.TemplateResponse(
                request,
                "public/form.html",
                {"form": form_detail, "error": str(exc), "submitted": False},
                status_code=400,
            )
        return redirect(f"/f/{slug}/success")

    @router.get("/{slug}/success", response_class=HTMLResponse)
    def public_success_page(request: Request, slug: str):
        return templates.TemplateResponse(request, "public/success.html", {"slug": slug})

    return router
