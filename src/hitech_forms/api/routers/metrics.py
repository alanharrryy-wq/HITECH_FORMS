from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from hitech_forms.db import get_session
from hitech_forms.db.repositories import WebhookOutboxRepository
from hitech_forms.platform.errors import not_found
from hitech_forms.platform.metrics import (
    increment_counter,
    render_text_metrics,
    set_gauge,
    snapshot_metrics,
)
from hitech_forms.platform.settings import get_settings


def build_metrics_router() -> APIRouter:
    router = APIRouter()

    @router.get("/metrics")
    def metrics(session: Session = Depends(get_session)):
        settings = get_settings()
        if not settings.feature_metrics:
            raise not_found("metrics endpoint is disabled")

        pending = WebhookOutboxRepository(session).count_pending()
        increment_counter("submissions_total", 0)
        increment_counter("webhook_delivered_total", 0)
        increment_counter("webhook_failed_total", 0)
        set_gauge("webhook_outbox_pending", pending)
        payload = render_text_metrics(snapshot_metrics())
        return Response(content=payload, media_type="text/plain; charset=utf-8", status_code=200)

    return router
