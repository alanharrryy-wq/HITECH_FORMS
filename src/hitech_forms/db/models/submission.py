from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hitech_forms.db.models.base import Base


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("form_id", "submission_seq", name="uq_submissions_form_seq"),
        Index("ix_submissions_form_id", "form_id"),
        Index("ix_submissions_form_seq", "form_id", "submission_seq"),
        Index("ix_submissions_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id", ondelete="CASCADE"), nullable=False)
    form_version_id: Mapped[int] = mapped_column(
        ForeignKey("form_versions.id", ondelete="CASCADE"), nullable=False
    )
    submission_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    answers = relationship("Answer", back_populates="submission", cascade="all, delete-orphan")
