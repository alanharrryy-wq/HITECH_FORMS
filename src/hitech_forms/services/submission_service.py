from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import date

from hitech_forms.contracts import (
    ANSWER_ORDER,
    FIELD_ORDER,
    FormRepositoryPort,
    SubmissionDetailDTO,
    SubmissionRepositoryPort,
    SubmissionSummaryDTO,
)
from hitech_forms.db.models import Field
from hitech_forms.platform.determinism import utc_now_epoch
from hitech_forms.platform.errors import bad_request
from hitech_forms.platform.slug import slugify

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SubmissionService:
    def __init__(self, form_repo: FormRepositoryPort, submission_repo: SubmissionRepositoryPort):
        self._form_repo = form_repo
        self._submission_repo = submission_repo

    def command_submit_public(self, *, slug: str, values: dict[str, str]) -> dict:
        form = self._form_repo.get_form_by_slug(slugify(slug))
        if form.status != "published":
            raise bad_request("form is not published")
        version = self._form_repo.get_active_version(form)
        if version.status != "published":
            raise bad_request(
                "active form version is not published",
                details={"form_id": form.id, "form_version_id": version.id},
            )
        fields = self._form_repo.get_fields_for_version(version.id)
        normalized_answers = self._validate_submission(fields, values)
        submission = self._submission_repo.create_submission(
            form_id=form.id,
            form_version_id=version.id,
            answers=normalized_answers,
            now_epoch=utc_now_epoch(),
        )
        return asdict(
            SubmissionSummaryDTO(
                id=submission.id,
                form_id=submission.form_id,
                form_version_id=submission.form_version_id,
                submission_seq=submission.submission_seq,
                created_at=submission.created_at,
            )
        )

    def query_list_submissions(self, *, form_id: int, page: int, page_size: int) -> dict:
        safe_page = 1 if page < 1 else page
        safe_size = 20 if page_size < 1 else min(page_size, 100)
        offset = (safe_page - 1) * safe_size
        rows, total = self._submission_repo.list_submissions(
            form_id=form_id,
            offset=offset,
            limit=safe_size,
        )
        items = [
            asdict(
                SubmissionSummaryDTO(
                    id=row.id,
                    form_id=row.form_id,
                    form_version_id=row.form_version_id,
                    submission_seq=row.submission_seq,
                    created_at=row.created_at,
                )
            )
            for row in rows
        ]
        return {
            "items": items,
            "total": total,
            "page": safe_page,
            "page_size": safe_size,
            "has_next": offset + safe_size < total,
        }

    def query_submission_detail(self, *, form_id: int, submission_id: int) -> dict:
        row = self._submission_repo.get_submission(form_id=form_id, submission_id=submission_id)
        answers = {
            item.field_key: item.value_text
            for item in sorted(row.answers, key=lambda x: getattr(x, ANSWER_ORDER[0]))
        }
        return asdict(
            SubmissionDetailDTO(
                id=row.id,
                form_id=row.form_id,
                form_version_id=row.form_version_id,
                submission_seq=row.submission_seq,
                created_at=row.created_at,
                answers=answers,
            )
        )

    def _validate_submission(self, fields: list[Field], values: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for field in sorted(fields, key=lambda x: (getattr(x, FIELD_ORDER[0]), getattr(x, FIELD_ORDER[1]))):
            incoming = values.get(field.field_key, "")
            normalized_value = self._normalize_by_type(field, incoming)
            if field.required and not normalized_value:
                raise bad_request(f"field '{field.label}' is required")
            normalized[field.field_key] = normalized_value
        return normalized

    def _normalize_by_type(self, field: Field, incoming: str) -> str:
        raw = str(incoming or "").strip()
        if field.type in {"text", "textarea"}:
            return raw
        if field.type == "number":
            if not raw:
                return ""
            try:
                float(raw)
            except ValueError as exc:
                raise bad_request(f"field '{field.label}' must be a number") from exc
            return raw
        if field.type == "email":
            if raw and not _EMAIL_RE.match(raw):
                raise bad_request(f"field '{field.label}' must be a valid email")
            return raw
        if field.type == "checkbox":
            return "true" if raw.lower() in {"1", "true", "on", "yes"} else "false"
        if field.type == "date":
            if not raw:
                return ""
            try:
                parsed = date.fromisoformat(raw)
            except ValueError as exc:
                raise bad_request(f"field '{field.label}' must be YYYY-MM-DD") from exc
            return parsed.isoformat()
        if field.type == "select":
            options = [str(item) for item in json.loads(field.config_json or "{}").get("options", [])]
            if raw and raw not in options:
                raise bad_request(f"field '{field.label}' has invalid option")
            return raw
        raise bad_request(f"unsupported field type '{field.type}'")
