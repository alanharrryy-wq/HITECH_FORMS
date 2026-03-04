from __future__ import annotations

from fastapi import Depends, Header, Query, Request
from sqlalchemy.orm import Session

from hitech_forms.app.security.rate_limit import InMemoryRateLimiter
from hitech_forms.contracts import ExportServicePort, FormServicePort, SubmissionServicePort
from hitech_forms.db import get_session
from hitech_forms.db.repositories import (
    FormRepository,
    SubmissionRepository,
    WebhookOutboxRepository,
)
from hitech_forms.platform.errors import AppError, unauthorized
from hitech_forms.platform.logging import get_logger, log_event, log_security_event
from hitech_forms.platform.settings import get_settings
from hitech_forms.services import (
    ExportService,
    FormService,
    SubmissionService,
    WebhookOutboxService,
)

_rate_limiter = InMemoryRateLimiter()
_logger = get_logger("hitech_forms.security")


def _rate_limit_identity(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _enforce_rate_limit(request: Request, *, scope: str, limit_rps: int) -> None:
    settings = get_settings()
    if not settings.feature_rate_limit or limit_rps <= 0:
        return
    identity = _rate_limit_identity(request)
    _rate_limiter.check(key=identity, scope=scope, limit_rps=limit_rps)


def enforce_public_submission_rate_limit(request: Request) -> None:
    settings = get_settings()
    try:
        _enforce_rate_limit(
            request,
            scope="public_submission",
            limit_rps=settings.rate_limit_rps_public,
        )
    except AppError:
        log_event(
            _logger,
            "rate_limit_triggered",
            scope="public_submission",
            method=request.method,
            path=request.url.path,
            client=_rate_limit_identity(request),
        )
        raise


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
            client=_rate_limit_identity(request),
        )
        raise unauthorized()
    try:
        _enforce_rate_limit(request, scope="admin", limit_rps=settings.rate_limit_rps_admin)
    except AppError:
        log_security_event(
            _logger,
            "rate_limit_triggered",
            scope="admin",
            method=request.method,
            path=request.url.path,
            client=_rate_limit_identity(request),
        )
        raise


def get_form_service(session: Session = Depends(get_session)) -> FormServicePort:
    return FormService(FormRepository(session))


def get_submission_service(session: Session = Depends(get_session)) -> SubmissionServicePort:
    settings = get_settings()
    webhook_service = WebhookOutboxService(WebhookOutboxRepository(session), settings)
    return SubmissionService(
        FormRepository(session),
        SubmissionRepository(session),
        webhook_outbox_service=webhook_service,
    )


def get_export_service(session: Session = Depends(get_session)) -> ExportServicePort:
    return ExportService(FormRepository(session), SubmissionRepository(session))


def reset_rate_limiter_cache() -> None:
    _rate_limiter.reset()
