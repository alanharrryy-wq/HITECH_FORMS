from __future__ import annotations

from fastapi import APIRouter, Depends

from hitech_forms.app.dependencies import admin_guard, get_submission_service
from hitech_forms.app.responses import canonical_json_response
from hitech_forms.contracts import SubmissionServicePort


def build_admin_submissions_router() -> APIRouter:
    router = APIRouter(prefix="/admin/forms", dependencies=[Depends(admin_guard)])

    @router.get("/{form_id}/submissions")
    def admin_list_submissions(
        form_id: int,
        page: int = 1,
        page_size: int = 20,
        submission_service: SubmissionServicePort = Depends(get_submission_service),
    ):
        return canonical_json_response(
            submission_service.query_list_submissions(form_id=form_id, page=page, page_size=page_size)
        )

    @router.get("/{form_id}/submissions/{submission_id}")
    def admin_get_submission(
        form_id: int,
        submission_id: int,
        submission_service: SubmissionServicePort = Depends(get_submission_service),
    ):
        return canonical_json_response(
            submission_service.query_submission_detail(form_id=form_id, submission_id=submission_id)
        )

    return router
