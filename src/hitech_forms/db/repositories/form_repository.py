from __future__ import annotations

import json
from typing import Any, cast

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from hitech_forms.db.models import Field, Form, FormVersion
from hitech_forms.platform.errors import not_found


class FormRepository:
    def __init__(self, session: Session):
        self._session = session

    def list_taken_slugs(self) -> set[str]:
        rows = self._session.execute(select(Form.slug)).scalars().all()
        return set(rows)

    def list_forms(self, *, offset: int, limit: int) -> tuple[list[Form], int]:
        total = self._session.execute(select(func.count(Form.id))).scalar_one()
        stmt = (
            select(Form)
            .order_by(Form.created_at.asc(), Form.id.asc())
            .offset(offset)
            .limit(limit)
        )
        forms = list(self._session.execute(stmt).scalars().all())
        return forms, int(total)

    def create_form(self, *, title: str, slug: str, now_epoch: int) -> Form:
        form = Form(title=title, slug=slug, status="draft", created_at=now_epoch, updated_at=now_epoch)
        self._session.add(form)
        self._session.flush()
        version = FormVersion(
            form_id=form.id,
            version_number=1,
            status="draft",
            created_at=now_epoch,
            published_at=None,
        )
        self._session.add(version)
        self._session.flush()
        form.active_version_id = version.id
        self._session.flush()
        return form

    def get_form(self, form_id: int) -> Form:
        self._session.expire_all()
        stmt: Select[tuple[Form]] = (
            select(Form)
            .where(Form.id == form_id)
            .options(joinedload(Form.versions).joinedload(FormVersion.fields))
        )
        form = self._session.execute(stmt).unique().scalars().first()
        if form is None:
            raise not_found("form not found")
        return form

    def get_form_by_slug(self, slug: str) -> Form:
        self._session.expire_all()
        stmt: Select[tuple[Form]] = (
            select(Form)
            .where(Form.slug == slug)
            .options(joinedload(Form.versions).joinedload(FormVersion.fields))
        )
        form = self._session.execute(stmt).unique().scalars().first()
        if form is None:
            raise not_found("form not found")
        return form

    def update_form_metadata(self, *, form: Form, title: str, slug: str, now_epoch: int) -> Form:
        form.title = title
        form.slug = slug
        form.updated_at = now_epoch
        self._session.flush()
        return form

    def delete_form(self, form: Form) -> None:
        self._session.delete(form)
        self._session.flush()

    def publish_form(self, *, form: Form, now_epoch: int) -> Form:
        active = self.get_active_version(form)
        form.status = "published"
        form.updated_at = now_epoch
        active.status = "published"
        active.published_at = now_epoch
        self._session.flush()
        return form

    def get_active_version(self, form: Form) -> FormVersion:
        if form.active_version_id is None:
            raise not_found("active form version not found")
        for version in form.versions:
            typed_version = cast(FormVersion, version)
            if typed_version.id == form.active_version_id:
                return typed_version
        stmt = select(FormVersion).where(FormVersion.id == form.active_version_id)
        version = self._session.execute(stmt).scalars().first()
        if version is None:
            raise not_found("active form version not found")
        return version

    def replace_fields(
        self,
        *,
        form_version_id: int,
        field_inputs: list[dict[str, Any]],
        now_epoch: int,
    ) -> list[Field]:
        old_fields = self._session.execute(
            select(Field).where(Field.form_version_id == form_version_id)
        ).scalars()
        for existing in old_fields:
            self._session.delete(existing)
        self._session.flush()

        inserted: list[Field] = []
        for payload in field_inputs:
            config_json = json.dumps(payload.get("config", {}), sort_keys=True, separators=(",", ":"))
            field = Field(
                form_version_id=form_version_id,
                field_key=str(payload["field_key"]),
                label=str(payload["label"]),
                type=str(payload["type"]),
                required=1 if payload.get("required") else 0,
                position=int(payload["position"]),
                config_json=config_json,
                created_at=now_epoch,
            )
            self._session.add(field)
            inserted.append(field)
        self._session.flush()
        return inserted

    def get_fields_for_version(self, form_version_id: int) -> list[Field]:
        stmt = (
            select(Field)
            .where(Field.form_version_id == form_version_id)
            .order_by(Field.position.asc(), Field.id.asc())
        )
        return list(self._session.execute(stmt).scalars().all())

    def slug_exists_for_other_form(self, slug: str, form_id: int) -> bool:
        stmt = select(Form.id).where(Form.slug == slug, Form.id != form_id)
        return self._session.execute(stmt).first() is not None
