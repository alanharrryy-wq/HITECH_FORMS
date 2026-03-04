"""0003_webhook_outbox

Revision ID: 0003_webhook_outbox
Revises: 0002_submission_seq
Create Date: 2026-02-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_webhook_outbox"
down_revision = "0002_submission_seq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("target_url", sa.String(length=1000), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("form_id", sa.Integer(), sa.ForeignKey("forms.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "form_version_id",
            sa.Integer(),
            sa.ForeignKey("form_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "submission_id",
            sa.Integer(),
            sa.ForeignKey("submissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.Integer(), nullable=True),
        sa.UniqueConstraint("idempotency_key", name="uq_webhook_outbox_idempotency_key"),
    )
    op.create_index(
        "ix_webhook_outbox_status_next_attempt_id",
        "webhook_outbox",
        ["status", "next_attempt_at", "id"],
        unique=False,
    )
    op.create_index("ix_webhook_outbox_submission_id", "webhook_outbox", ["submission_id"], unique=False)
    op.create_index("ix_webhook_outbox_created_at", "webhook_outbox", ["created_at"], unique=False)

    op.create_table(
        "webhook_delivery_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "outbox_id",
            sa.Integer(),
            sa.ForeignKey("webhook_outbox.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempted_at", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("response_snippet", sa.Text(), nullable=False, server_default=""),
        sa.Column("error_type", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.UniqueConstraint("outbox_id", "attempt_no", name="uq_webhook_delivery_log_attempt"),
    )
    op.create_index(
        "ix_webhook_delivery_log_outbox_id",
        "webhook_delivery_log",
        ["outbox_id"],
        unique=False,
    )
    op.create_index(
        "ix_webhook_delivery_log_attempted_at",
        "webhook_delivery_log",
        ["attempted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_delivery_log_attempted_at", table_name="webhook_delivery_log")
    op.drop_index("ix_webhook_delivery_log_outbox_id", table_name="webhook_delivery_log")
    op.drop_table("webhook_delivery_log")

    op.drop_index("ix_webhook_outbox_created_at", table_name="webhook_outbox")
    op.drop_index("ix_webhook_outbox_submission_id", table_name="webhook_outbox")
    op.drop_index("ix_webhook_outbox_status_next_attempt_id", table_name="webhook_outbox")
    op.drop_table("webhook_outbox")
