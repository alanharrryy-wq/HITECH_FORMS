"""0002_submission_seq

Revision ID: 0002_submission_seq
Revises: 0001_initial
Create Date: 2026-02-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_submission_seq"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("submission_seq", sa.Integer(), nullable=False, server_default="0"))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, form_id FROM submissions ORDER BY form_id ASC, created_at ASC, id ASC")
    ).fetchall()
    seq_by_form: dict[int, int] = {}
    for row in rows:
        form_id = int(row.form_id)
        seq_by_form[form_id] = seq_by_form.get(form_id, 0) + 1
        bind.execute(
            sa.text("UPDATE submissions SET submission_seq = :submission_seq WHERE id = :submission_id"),
            {"submission_seq": seq_by_form[form_id], "submission_id": int(row.id)},
        )

    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_submissions_form_seq", ["form_id", "submission_seq"])
        batch_op.create_index("ix_submissions_form_seq", ["form_id", "submission_seq"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.drop_index("ix_submissions_form_seq")
        batch_op.drop_constraint("uq_submissions_form_seq", type_="unique")
        batch_op.drop_column("submission_seq")
