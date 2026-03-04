from __future__ import annotations

import time
from dataclasses import dataclass

from hitech_forms.db import session_scope
from hitech_forms.db.repositories import WebhookOutboxRepository
from hitech_forms.db.repositories.webhook_outbox_repository import FAILED
from hitech_forms.platform.determinism import utc_now_epoch
from hitech_forms.platform.logging import get_logger, log_event
from hitech_forms.platform.metrics import increment_counter
from hitech_forms.platform.settings import Settings, get_settings
from hitech_forms.services.webhooks.http_client import WebhookDeliveryResult, WebhookHttpClient
from hitech_forms.services.webhooks.scheduler import next_attempt_epoch


def _last_error_for(result: WebhookDeliveryResult) -> str:
    if result.error_message:
        return result.error_message[:300]
    if result.http_status is not None:
        return f"http status {result.http_status}"
    return "delivery failed"


@dataclass(frozen=True)
class WebhookWorkerSummary:
    processed: int
    delivered: int
    retried: int
    failed: int


class WebhookWorker:
    def __init__(self, settings: Settings | None = None, http_client: WebhookHttpClient | None = None):
        self._settings = settings or get_settings()
        self._http_client = http_client or WebhookHttpClient()
        self._logger = get_logger("hitech_forms.webhooks.worker")

    def run_once(self, *, limit: int = 50) -> WebhookWorkerSummary:
        if not self._settings.feature_webhooks_outbox:
            return WebhookWorkerSummary(processed=0, delivered=0, retried=0, failed=0)

        processed = 0
        delivered = 0
        retried = 0
        failed = 0

        while processed < max(1, limit):
            with session_scope() as session:
                repo = WebhookOutboxRepository(session)
                now_epoch = utc_now_epoch()
                row = repo.claim_next_eligible(now_epoch=now_epoch)
                if row is None:
                    break

                attempt_no = row.attempt_count + 1
                result = self._http_client.deliver(
                    target_url=row.target_url,
                    payload_json=row.payload_json,
                    idempotency_key=row.idempotency_key,
                )
                repo.append_delivery_log(
                    outbox_id=row.id,
                    attempt_no=attempt_no,
                    attempted_at=now_epoch,
                    http_status=result.http_status,
                    response_snippet=result.response_snippet,
                    error_type=result.error_type,
                    error_message=result.error_message,
                )

                if result.delivered:
                    repo.mark_delivered(row=row, delivered_at=now_epoch, attempt_count=attempt_no)
                    increment_counter("webhook_delivered_total", 1)
                    delivered += 1
                    log_event(
                        self._logger,
                        "webhook_delivered",
                        outbox_id=row.id,
                        attempt_no=attempt_no,
                        http_status=result.http_status or 200,
                    )
                else:
                    last_error = _last_error_for(result)
                    if attempt_no >= self._settings.webhook_max_attempts:
                        repo.mark_failed(row=row, attempt_count=attempt_no, last_error=last_error)
                        increment_counter("webhook_failed_total", 1)
                        failed += 1
                        log_event(
                            self._logger,
                            "webhook_failed",
                            outbox_id=row.id,
                            attempt_no=attempt_no,
                            status=FAILED,
                            error=last_error,
                        )
                    else:
                        next_at = next_attempt_epoch(
                            now_epoch=now_epoch,
                            base_backoff_seconds=self._settings.webhook_base_backoff_seconds,
                            attempt_count=row.attempt_count,
                            payload_sha256=row.payload_sha256,
                            max_jitter_seconds=self._settings.webhook_jitter,
                        )
                        repo.mark_retry(
                            row=row,
                            attempt_count=attempt_no,
                            next_attempt_at=next_at,
                            last_error=last_error,
                        )
                        retried += 1
                        log_event(
                            self._logger,
                            "webhook_retry_scheduled",
                            outbox_id=row.id,
                            attempt_no=attempt_no,
                            next_attempt_at=next_at,
                            error=last_error,
                        )
                processed += 1

        return WebhookWorkerSummary(
            processed=processed,
            delivered=delivered,
            retried=retried,
            failed=failed,
        )

    def run_loop(self, *, interval_seconds: int = 5, limit: int = 50) -> None:
        sleep_seconds = max(1, interval_seconds)
        while True:
            try:
                summary = self.run_once(limit=limit)
                log_event(
                    self._logger,
                    "webhook_worker_tick",
                    processed=summary.processed,
                    delivered=summary.delivered,
                    retried=summary.retried,
                    failed=summary.failed,
                )
            except Exception as exc:  # pragma: no cover - defensive logging in loop
                log_event(
                    self._logger,
                    "webhook_worker_error",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
            time.sleep(sleep_seconds)
