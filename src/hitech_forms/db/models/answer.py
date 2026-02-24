from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hitech_forms.db.models.base import Base


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        Index("ix_answers_submission_id", "submission_id"),
        Index("ix_answers_field_key", "field_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    field_key: Mapped[str] = mapped_column(String(120), nullable=False)
    value_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    submission = relationship("Submission", back_populates="answers")
