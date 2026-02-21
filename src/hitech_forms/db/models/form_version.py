from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hitech_forms.db.models.base import Base


class FormVersion(Base):
    __tablename__ = "form_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[int | None] = mapped_column(Integer, nullable=True)

    form = relationship("Form", back_populates="versions")
    fields = relationship("Field", back_populates="form_version", cascade="all, delete-orphan")
