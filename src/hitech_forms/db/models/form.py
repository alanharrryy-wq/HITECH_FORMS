from __future__ import annotations

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hitech_forms.db.models.base import Base


class Form(Base):
    __tablename__ = "forms"
    __table_args__ = (
        Index("ix_forms_slug", "slug"),
        Index("ix_forms_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    active_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    versions = relationship(
        "FormVersion",
        back_populates="form",
        cascade="all, delete-orphan",
        foreign_keys="FormVersion.form_id",
    )
