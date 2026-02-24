from __future__ import annotations

import csv
import io
from collections.abc import Iterator

from hitech_forms.contracts import (
    EXPORT_VERSION_V1,
    FIELD_ORDER,
    FormRepositoryPort,
    SubmissionRepositoryPort,
)
from hitech_forms.platform.errors import bad_request


class ExportService:
    def __init__(self, form_repo: FormRepositoryPort, submission_repo: SubmissionRepositoryPort):
        self._form_repo = form_repo
        self._submission_repo = submission_repo

    def stream_form_csv(self, *, form_id: int, export_version: str = "v1") -> Iterator[str]:
        if export_version != EXPORT_VERSION_V1:
            raise bad_request("unsupported export version")
        form = self._form_repo.get_form(form_id)
        version = self._form_repo.get_active_version(form)
        fields = self._form_repo.get_fields_for_version(version.id)
        ordered_field_keys = [
            field.field_key
            for field in sorted(fields, key=lambda x: (getattr(x, FIELD_ORDER[0]), getattr(x, FIELD_ORDER[1])))
        ]
        header = ["submission_id", "created_at", *ordered_field_keys]

        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(header)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        for submission in self._submission_repo.iter_submissions_for_export(form.id):
            answer_map = {answer.field_key: answer.value_text for answer in submission.answers}
            row = [str(submission.id), str(submission.created_at)]
            for key in ordered_field_keys:
                row.append(answer_map.get(key, ""))
            writer.writerow(row)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)
