from __future__ import annotations

import hashlib
from typing import Any

from hitech_forms.platform.determinism import canonical_json_dumps


def canonical_payload_json(payload: dict[str, Any]) -> str:
    return canonical_json_dumps(payload)


def payload_sha256(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def derive_idempotency_key(*, form_version_id: int, submission_id: int, target_url: str) -> str:
    seed = f"{form_version_id}:{submission_id}:{target_url}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def build_submission_payload(
    *,
    form_id: int,
    form_version_id: int,
    submission_id: int,
    submission_seq: int,
    created_at: int,
    slug: str,
    answers: dict[str, str],
) -> dict[str, Any]:
    ordered_answers = {key: answers[key] for key in sorted(answers)}
    return {
        "event": "submission.accepted",
        "form_id": form_id,
        "form_slug": slug,
        "form_version_id": form_version_id,
        "submission": {
            "id": submission_id,
            "submission_seq": submission_seq,
            "created_at": created_at,
            "answers": ordered_answers,
        },
    }
