from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hitech_forms.db.models.base import Base


class WebhookDeliveryLog(Base):
    __tablename__ = "webhook_delivery_log"
    __table_args__ = (
        UniqueConstraint("outbox_id", "attempt_no", name="uq_webhook_delivery_log_attempt"),
        Index("ix_webhook_delivery_log_outbox_id", "outbox_id"),
        Index("ix_webhook_delivery_log_attempted_at", "attempted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    outbox_id: Mapped[int] = mapped_column(
        ForeignKey("webhook_outbox.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempted_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    outbox = relationship("WebhookOutbox", back_populates="delivery_logs")
