from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FieldDTO:
    id: int
    key: str
    label: str
    field_type: str
    required: bool
    position: int
    options: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FormSummaryDTO:
    id: int
    title: str
    slug: str
    status: str
    created_at: int
    updated_at: int


@dataclass(frozen=True)
class FormDetailDTO:
    id: int
    title: str
    slug: str
    status: str
    active_version_id: int
    fields: list[FieldDTO]
    created_at: int
    updated_at: int


@dataclass(frozen=True)
class SubmissionSummaryDTO:
    id: int
    form_id: int
    form_version_id: int
    submission_seq: int
    created_at: int


@dataclass(frozen=True)
class SubmissionDetailDTO:
    id: int
    form_id: int
    form_version_id: int
    submission_seq: int
    created_at: int
    answers: dict[str, str]


@dataclass(frozen=True)
class ErrorDTO:
    code: str
    message: str
    details: dict[str, Any] | None = None
