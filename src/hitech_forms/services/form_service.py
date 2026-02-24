from __future__ import annotations

import json
from dataclasses import asdict

from hitech_forms.contracts import (
    FIELD_ORDER,
    FieldDTO,
    FormDetailDTO,
    FormRepositoryPort,
    FormSummaryDTO,
)
from hitech_forms.db.models import Field, Form
from hitech_forms.platform.determinism import stable_sorted, utc_now_epoch
from hitech_forms.platform.errors import bad_request, conflict, not_found
from hitech_forms.platform.slug import slugify, stable_slug

ALLOWED_FIELD_TYPES = {"text", "textarea", "number", "email", "select", "checkbox", "date"}


class FormService:
    def __init__(self, form_repo: FormRepositoryPort):
        self._form_repo = form_repo

    def query_list_forms(self, *, page: int, page_size: int) -> dict:
        safe_page = 1 if page < 1 else page
        safe_size = 20 if page_size < 1 else min(page_size, 100)
        offset = (safe_page - 1) * safe_size
        forms, total = self._form_repo.list_forms(offset=offset, limit=safe_size)
        items = [asdict(self._to_form_summary(row)) for row in forms]
        return {
            "items": items,
            "total": total,
            "page": safe_page,
            "page_size": safe_size,
            "has_next": offset + safe_size < total,
        }

    def command_create_form(self, *, title: str, slug: str | None = None) -> dict:
        title_value = title.strip()
        if not title_value:
            raise bad_request("title is required")
        taken = self._form_repo.list_taken_slugs()
        base = slugify(slug) if slug else slugify(title_value)
        final_slug = stable_slug(base, taken)
        now_epoch = utc_now_epoch()
        created = self._form_repo.create_form(title=title_value, slug=final_slug, now_epoch=now_epoch)
        return asdict(self._to_form_detail(created))

    def query_form_detail(self, form_id: int) -> dict:
        form = self._form_repo.get_form(form_id)
        return asdict(self._to_form_detail(form))

    def command_update_form(self, *, form_id: int, title: str, slug: str | None) -> dict:
        form = self._form_repo.get_form(form_id)
        title_value = title.strip()
        if not title_value:
            raise bad_request("title is required")
        sanitized_slug = slugify(slug or title_value)
        if self._form_repo.slug_exists_for_other_form(sanitized_slug, form.id):
            raise conflict("slug already exists")
        updated = self._form_repo.update_form_metadata(
            form=form,
            title=title_value,
            slug=sanitized_slug,
            now_epoch=utc_now_epoch(),
        )
        return asdict(self._to_form_detail(updated))

    def command_delete_form(self, form_id: int) -> None:
        form = self._form_repo.get_form(form_id)
        self._form_repo.delete_form(form)

    def command_replace_fields(self, *, form_id: int, fields: list[dict]) -> dict:
        form = self._form_repo.get_form(form_id)
        active_version = self._form_repo.get_active_version(form)
        if active_version.status == "published":
            raise conflict(
                "published form version is immutable",
                details={"form_id": form_id, "form_version_id": active_version.id},
            )
        normalized = self._normalize_fields(fields)
        now_epoch = utc_now_epoch()
        self._form_repo.replace_fields(
            form_version_id=active_version.id,
            field_inputs=normalized,
            now_epoch=now_epoch,
        )
        form.updated_at = now_epoch
        refreshed = self._form_repo.get_form(form_id)
        return asdict(self._to_form_detail(refreshed))

    def command_publish_form(self, form_id: int) -> dict:
        form = self._form_repo.get_form(form_id)
        active_fields = self._form_repo.get_fields_for_version(form.active_version_id or 0)
        if not active_fields:
            raise bad_request("cannot publish form without fields")
        published = self._form_repo.publish_form(form=form, now_epoch=utc_now_epoch())
        return asdict(self._to_form_detail(published))

    def query_public_form(self, slug: str) -> dict:
        form = self._form_repo.get_form_by_slug(slugify(slug))
        if form.status != "published":
            raise not_found("published form not found")
        return asdict(self._to_form_detail(form))

    def _to_form_summary(self, form: Form) -> FormSummaryDTO:
        return FormSummaryDTO(
            id=form.id,
            title=form.title,
            slug=form.slug,
            status=form.status,
            created_at=form.created_at,
            updated_at=form.updated_at,
        )

    def _to_form_detail(self, form: Form) -> FormDetailDTO:
        active = self._form_repo.get_active_version(form)
        fields = [
            self._to_field_dto(row)
            for row in stable_sorted(
                active.fields,
                key=lambda x: (getattr(x, FIELD_ORDER[0]), getattr(x, FIELD_ORDER[1])),
            )
        ]
        return FormDetailDTO(
            id=form.id,
            title=form.title,
            slug=form.slug,
            status=form.status,
            active_version_id=active.id,
            fields=fields,
            created_at=form.created_at,
            updated_at=form.updated_at,
        )

    def _to_field_dto(self, row: Field) -> FieldDTO:
        config = json.loads(row.config_json or "{}")
        options = [str(item) for item in config.get("options", [])]
        return FieldDTO(
            id=row.id,
            key=row.field_key,
            label=row.label,
            field_type=row.type,
            required=bool(row.required),
            position=row.position,
            options=options,
        )

    def _normalize_fields(self, fields: list[dict]) -> list[dict]:
        normalized: list[dict] = []
        seen_keys: set[str] = set()
        for idx, raw in enumerate(fields):
            key = slugify(str(raw.get("key", ""))).replace("-", "_")
            if not key:
                raise bad_request("field key is required")
            if key in seen_keys:
                raise conflict(f"duplicate field key: {key}")
            seen_keys.add(key)

            label = str(raw.get("label", "")).strip()
            if not label:
                raise bad_request("field label is required")
            field_type = str(raw.get("type", "text")).strip().lower()
            if field_type not in ALLOWED_FIELD_TYPES:
                raise bad_request(f"unsupported field type: {field_type}")
            required = bool(raw.get("required", False))
            options: list[str] = []
            if field_type == "select":
                option_raw = raw.get("options", [])
                options = [str(item).strip() for item in option_raw if str(item).strip()]
                if not options:
                    raise bad_request("select field requires options")
            normalized.append(
                {
                    "field_key": key,
                    "label": label,
                    "type": field_type,
                    "required": required,
                    "position": idx,
                    "config": {"options": options},
                }
            )
        return normalized
