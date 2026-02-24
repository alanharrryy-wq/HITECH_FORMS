"""0001_initial

Revision ID: 0001_initial
Revises:
Create Date: 2026-02-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False, unique=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("active_version_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_forms_slug", "forms", ["slug"], unique=False)
    op.create_index("ix_forms_created_at", "forms", ["created_at"], unique=False)

    op.create_table(
        "form_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("form_id", sa.Integer(), sa.ForeignKey("forms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.Integer(), nullable=True),
        sa.UniqueConstraint("form_id", "version_number", name="uq_form_version"),
    )
    op.create_index("ix_form_versions_form_id", "form_versions", ["form_id"], unique=False)
    op.create_index("ix_form_versions_created_at", "form_versions", ["created_at"], unique=False)

    op.create_table(
        "fields",
        sa.Column(
            "form_version_id",
            sa.Integer(),
            sa.ForeignKey("form_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("field_key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False, server_default="text"),
        sa.Column("required", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("form_version_id", "field_key", name="uq_field_key_per_version"),
    )
    op.create_index("ix_fields_form_version_id", "fields", ["form_version_id"], unique=False)
    op.create_index("ix_fields_position", "fields", ["position"], unique=False)

    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("form_id", sa.Integer(), sa.ForeignKey("forms.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "form_version_id",
            sa.Integer(),
            sa.ForeignKey("form_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_submissions_form_id", "submissions", ["form_id"], unique=False)
    op.create_index("ix_submissions_created_at", "submissions", ["created_at"], unique=False)

    op.create_table(
        "answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "submission_id",
            sa.Integer(),
            sa.ForeignKey("submissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_key", sa.String(length=120), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_answers_submission_id", "answers", ["submission_id"], unique=False)
    op.create_index("ix_answers_field_key", "answers", ["field_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_answers_field_key", table_name="answers")
    op.drop_index("ix_answers_submission_id", table_name="answers")
    op.drop_table("answers")

    op.drop_index("ix_submissions_created_at", table_name="submissions")
    op.drop_index("ix_submissions_form_id", table_name="submissions")
    op.drop_table("submissions")

    op.drop_index("ix_fields_position", table_name="fields")
    op.drop_index("ix_fields_form_version_id", table_name="fields")
    op.drop_table("fields")

    op.drop_index("ix_form_versions_created_at", table_name="form_versions")
    op.drop_index("ix_form_versions_form_id", table_name="form_versions")
    op.drop_table("form_versions")

    op.drop_index("ix_forms_created_at", table_name="forms")
    op.drop_index("ix_forms_slug", table_name="forms")
    op.drop_table("forms")
