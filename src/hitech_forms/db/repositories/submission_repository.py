from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session, selectinload

from hitech_forms.contracts import SUBMISSION_ORDER
from hitech_forms.db.models import Answer, Submission
from hitech_forms.platform.errors import not_found


class SubmissionRepository:
    def __init__(self, session: Session):
        self._session = session

    def create_submission(
        self,
        *,
        form_id: int,
        form_version_id: int,
        answers: dict[str, str],
        now_epoch: int,
    ) -> Submission:
        next_submission_seq = (
            select(func.coalesce(func.max(Submission.submission_seq), 0) + 1)
            .where(Submission.form_id == form_id)
            .scalar_subquery()
        )
        insert_stmt = (
            insert(Submission)
            .values(
                form_id=form_id,
                form_version_id=form_version_id,
                submission_seq=next_submission_seq,
                created_at=now_epoch,
            )
            .returning(Submission.id)
        )
        submission_id = int(self._session.execute(insert_stmt).scalar_one())
        submission = self._session.get(Submission, submission_id)
        if submission is None:
            raise not_found("submission not found")

        answer_rows = [
            Answer(
                submission_id=submission.id,
                field_key=field_key,
                value_text=value,
                created_at=now_epoch,
            )
            for field_key, value in sorted(answers.items(), key=lambda item: item[0])
        ]
        self._session.add_all(answer_rows)
        self._session.flush()
        return submission

    def list_submissions(self, *, form_id: int, offset: int, limit: int) -> tuple[list[Submission], int]:
        total = self._session.execute(
            select(func.count(Submission.id)).where(Submission.form_id == form_id)
        ).scalar_one()
        stmt = (
            select(Submission)
            .where(Submission.form_id == form_id)
            .order_by(
                getattr(Submission, SUBMISSION_ORDER[0]).asc(),
                getattr(Submission, SUBMISSION_ORDER[1]).asc(),
            )
            .offset(offset)
            .limit(limit)
        )
        rows = list(self._session.execute(stmt).scalars().all())
        return rows, int(total)

    def get_submission(self, *, form_id: int, submission_id: int) -> Submission:
        stmt = (
            select(Submission)
            .where(Submission.form_id == form_id, Submission.id == submission_id)
            .options(selectinload(Submission.answers))
        )
        submission = self._session.execute(stmt).scalars().first()
        if submission is None:
            raise not_found("submission not found")
        return submission

    def iter_submissions_for_export(self, form_id: int) -> Iterator[Submission]:
        stmt = (
            select(Submission)
            .where(Submission.form_id == form_id)
            .order_by(
                getattr(Submission, SUBMISSION_ORDER[0]).asc(),
                getattr(Submission, SUBMISSION_ORDER[1]).asc(),
            )
            .options(selectinload(Submission.answers))
        )
        yield from self._session.execute(stmt).scalars()
