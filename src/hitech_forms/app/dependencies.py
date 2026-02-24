from __future__ import annotations

from fastapi import Depends, Header, Query, Request
from sqlalchemy.orm import Session

from hitech_forms.app.security.rate_limit import InMemoryRateLimiter
from hitech_forms.contracts import ExportServicePort, FormServicePort, SubmissionServicePort
from hitech_forms.db import get_session
from hitech_forms.db.repositories import FormRepository, SubmissionRepository
from hitech_forms.platform.errors import unauthorized
from hitech_forms.platform.logging import get_logger, log_security_event
from hitech_forms.platform.settings import get_settings
from hitech_forms.services import ExportService, FormService, SubmissionService

_rate_limiter = InMemoryRateLimiter()
_logger = get_logger("hitech_forms.security")


async def admin_guard(
    request: Request,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    token: str | None = Query(default=None),
) -> None:
    settings = get_settings()
    candidate = (x_admin_token or token or "").strip()
    content_type = request.headers.get("content-type", "")
    if not candidate and (
        content_type.startswith("application/x-www-form-urlencoded")
        or content_type.startswith("multipart/form-data")
    ):
        form_data = await request.form()
        candidate = str(form_data.get("token", "")).strip()
    if candidate != settings.admin_token:
        log_security_event(
            _logger,
            "admin_auth_failed",
            method=request.method,
            path=request.url.path,
            client=(request.client.host if request.client else "unknown"),
        )
        raise unauthorized()
    scope = "admin"
    identity = request.client.host if request.client else "unknown"
    _rate_limiter.check(key=identity, scope=scope, limit_per_minute=settings.rate_limit_per_minute)


def get_form_service(session: Session = Depends(get_session)) -> FormServicePort:
    return FormService(FormRepository(session))


def get_submission_service(session: Session = Depends(get_session)) -> SubmissionServicePort:
    return SubmissionService(FormRepository(session), SubmissionRepository(session))


def get_export_service(session: Session = Depends(get_session)) -> ExportServicePort:
    return ExportService(FormRepository(session), SubmissionRepository(session))
