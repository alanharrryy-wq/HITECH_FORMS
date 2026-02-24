from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hitech_forms.app.dependencies import get_form_service, get_submission_service
from hitech_forms.app.responses import canonical_json_response
from hitech_forms.contracts import FormServicePort, SubmissionServicePort


class SubmitFormRequest(BaseModel):
    values: dict[str, str]


def build_public_forms_router() -> APIRouter:
    router = APIRouter(prefix="/f")

    @router.get("/{slug}")
    def public_get_form(slug: str, form_service: FormServicePort = Depends(get_form_service)):
        return canonical_json_response(form_service.query_public_form(slug))

    @router.post("/{slug}/submit")
    def public_submit_form(
        slug: str,
        payload: SubmitFormRequest,
        submission_service: SubmissionServicePort = Depends(get_submission_service),
    ):
        created: dict[str, Any] = submission_service.command_submit_public(slug=slug, values=payload.values)
        return canonical_json_response(created, status_code=201)

    return router
