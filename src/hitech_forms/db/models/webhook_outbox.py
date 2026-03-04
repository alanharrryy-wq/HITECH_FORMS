from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hitech_forms.db.models.base import Base


class WebhookOutbox(Base):
    __tablename__ = "webhook_outbox"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_webhook_outbox_idempotency_key"),
        Index("ix_webhook_outbox_status_next_attempt_id", "status", "next_attempt_at", "id"),
        Index("ix_webhook_outbox_submission_id", "submission_id"),
        Index("ix_webhook_outbox_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    target_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id", ondelete="CASCADE"), nullable=False)
    form_version_id: Mapped[int] = mapped_column(
        ForeignKey("form_versions.id", ondelete="CASCADE"), nullable=False
    )
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[int | None] = mapped_column(Integer, nullable=True)

    delivery_logs = relationship(
        "WebhookDeliveryLog",
        back_populates="outbox",
        cascade="all, delete-orphan",
    )
