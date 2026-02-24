from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hitech_forms.db.models.base import Base


class FormVersion(Base):
    __tablename__ = "form_versions"
    __table_args__ = (
        UniqueConstraint("form_id", "version_number", name="uq_form_version"),
        Index("ix_form_versions_form_id", "form_id"),
        Index("ix_form_versions_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[int | None] = mapped_column(Integer, nullable=True)

    form = relationship("Form", back_populates="versions", foreign_keys=[form_id])
    fields = relationship("Field", back_populates="form_version", cascade="all, delete-orphan")
