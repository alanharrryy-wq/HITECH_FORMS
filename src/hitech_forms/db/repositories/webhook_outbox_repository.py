from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from hitech_forms.db.models import WebhookDeliveryLog, WebhookOutbox

PENDING = "PENDING"
IN_FLIGHT = "IN_FLIGHT"
DELIVERED = "DELIVERED"
FAILED = "FAILED"


class WebhookOutboxRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_by_idempotency_key(self, idempotency_key: str) -> WebhookOutbox | None:
        stmt = select(WebhookOutbox).where(WebhookOutbox.idempotency_key == idempotency_key).limit(1)
        return self._session.execute(stmt).scalars().first()

    def create_outbox(
        self,
        *,
        created_at: int,
        next_attempt_at: int,
        target_url: str,
        payload_json: str,
        payload_sha256: str,
        idempotency_key: str,
        form_id: int,
        form_version_id: int,
        submission_id: int,
    ) -> WebhookOutbox:
        row = WebhookOutbox(
            created_at=created_at,
            next_attempt_at=next_attempt_at,
            attempt_count=0,
            status=PENDING,
            target_url=target_url,
            payload_json=payload_json,
            payload_sha256=payload_sha256,
            idempotency_key=idempotency_key,
            form_id=form_id,
            form_version_id=form_version_id,
            submission_id=submission_id,
            last_error=None,
            delivered_at=None,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def count_pending(self) -> int:
        stmt = select(func.count(WebhookOutbox.id)).where(WebhookOutbox.status == PENDING)
        total = self._session.execute(stmt).scalar_one()
        return int(total)

    def claim_next_eligible(self, *, now_epoch: int) -> WebhookOutbox | None:
        for _ in range(8):
            candidate_id = self._session.execute(
                select(WebhookOutbox.id)
                .where(
                    WebhookOutbox.status == PENDING,
                    WebhookOutbox.next_attempt_at <= now_epoch,
                )
                .order_by(WebhookOutbox.next_attempt_at.asc(), WebhookOutbox.id.asc())
                .limit(1)
            ).scalar_one_or_none()
            if candidate_id is None:
                return None

            claimed = self._session.execute(
                update(WebhookOutbox)
                .where(
                    WebhookOutbox.id == int(candidate_id),
                    WebhookOutbox.status == PENDING,
                    WebhookOutbox.next_attempt_at <= now_epoch,
                )
                .values(status=IN_FLIGHT)
            )
            if int(getattr(claimed, "rowcount", 0)) == 1:
                self._session.flush()
                row = self._session.get(WebhookOutbox, int(candidate_id))
                if row is not None:
                    return row
        return None

    def append_delivery_log(
        self,
        *,
        outbox_id: int,
        attempt_no: int,
        attempted_at: int,
        http_status: int | None,
        response_snippet: str,
        error_type: str | None,
        error_message: str | None,
    ) -> WebhookDeliveryLog:
        row = WebhookDeliveryLog(
            outbox_id=outbox_id,
            attempt_no=attempt_no,
            attempted_at=attempted_at,
            http_status=http_status,
            response_snippet=response_snippet,
            error_type=error_type,
            error_message=error_message,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def mark_delivered(self, *, row: WebhookOutbox, delivered_at: int, attempt_count: int) -> None:
        row.status = DELIVERED
        row.attempt_count = attempt_count
        row.delivered_at = delivered_at
        row.last_error = None
        self._session.flush()

    def mark_retry(
        self,
        *,
        row: WebhookOutbox,
        attempt_count: int,
        next_attempt_at: int,
        last_error: str,
    ) -> None:
        row.status = PENDING
        row.attempt_count = attempt_count
        row.next_attempt_at = next_attempt_at
        row.last_error = last_error
        self._session.flush()

    def mark_failed(self, *, row: WebhookOutbox, attempt_count: int, last_error: str) -> None:
        row.status = FAILED
        row.attempt_count = attempt_count
        row.last_error = last_error
        self._session.flush()
