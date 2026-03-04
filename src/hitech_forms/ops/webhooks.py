from __future__ import annotations

from hitech_forms.platform.settings import get_settings
from hitech_forms.services.webhooks import WebhookWorker


def webhooks_run_once(*, limit: int = 50) -> dict[str, int]:
    worker = WebhookWorker(settings=get_settings())
    summary = worker.run_once(limit=limit)
    return {
        "processed": summary.processed,
        "delivered": summary.delivered,
        "retried": summary.retried,
        "failed": summary.failed,
    }


def webhooks_run_loop(*, interval_seconds: int = 5, limit: int = 50) -> None:
    worker = WebhookWorker(settings=get_settings())
    worker.run_loop(interval_seconds=interval_seconds, limit=limit)
