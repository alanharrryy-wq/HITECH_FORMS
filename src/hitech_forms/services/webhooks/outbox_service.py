from __future__ import annotations

from dataclasses import dataclass

from hitech_forms.db.repositories import WebhookOutboxRepository
from hitech_forms.platform.logging import get_logger, log_event
from hitech_forms.platform.settings import Settings
from hitech_forms.services.webhooks.payloads import (
    build_submission_payload,
    canonical_payload_json,
    derive_idempotency_key,
    payload_sha256,
)


@dataclass(frozen=True)
class WebhookEnqueueResult:
    outbox_id: int
    enqueued: bool
    idempotency_key: str
    status: str


class WebhookOutboxService:
    def __init__(self, repo: WebhookOutboxRepository, settings: Settings):
        self._repo = repo
        self._settings = settings
        self._logger = get_logger("hitech_forms.webhooks.outbox")

    def is_enabled_and_configured(self) -> bool:
        return self._settings.feature_webhooks_outbox and bool(self._settings.webhook_target_url)

    def enqueue_submission(
        self,
        *,
        form_id: int,
        form_version_id: int,
        submission_id: int,
        submission_seq: int,
        created_at: int,
        slug: str,
        answers: dict[str, str],
    ) -> WebhookEnqueueResult | None:
        if not self.is_enabled_and_configured():
            return None

        target_url = self._settings.webhook_target_url
        idempotency_key = derive_idempotency_key(
            form_version_id=form_version_id,
            submission_id=submission_id,
            target_url=target_url,
        )
        existing = self._repo.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return WebhookEnqueueResult(
                outbox_id=existing.id,
                enqueued=False,
                idempotency_key=idempotency_key,
                status=existing.status,
            )

        payload = build_submission_payload(
            form_id=form_id,
            form_version_id=form_version_id,
            submission_id=submission_id,
            submission_seq=submission_seq,
            created_at=created_at,
            slug=slug,
            answers=answers,
        )
        payload_json = canonical_payload_json(payload)
        row = self._repo.create_outbox(
            created_at=created_at,
            next_attempt_at=created_at,
            target_url=target_url,
            payload_json=payload_json,
            payload_sha256=payload_sha256(payload_json),
            idempotency_key=idempotency_key,
            form_id=form_id,
            form_version_id=form_version_id,
            submission_id=submission_id,
        )
        log_event(
            self._logger,
            "webhook_enqueued",
            outbox_id=row.id,
            form_id=form_id,
            submission_id=submission_id,
            idempotency_key=idempotency_key,
        )
        return WebhookEnqueueResult(
            outbox_id=row.id,
            enqueued=True,
            idempotency_key=idempotency_key,
            status=row.status,
        )
