from __future__ import annotations

import pytest

from hitech_forms.app.security.rate_limit import InMemoryRateLimiter
from hitech_forms.platform.determinism import freeze_clock
from hitech_forms.platform.errors import AppError
from hitech_forms.services.webhooks.payloads import (
    build_submission_payload,
    canonical_payload_json,
    derive_idempotency_key,
    payload_sha256,
)
from hitech_forms.services.webhooks.scheduler import (
    compute_backoff_seconds,
    deterministic_jitter_seconds,
    next_attempt_epoch,
)


def test_webhook_payload_canonical_and_hash_stable():
    payload = build_submission_payload(
        form_id=1,
        form_version_id=2,
        submission_id=3,
        submission_seq=4,
        created_at=1700000000,
        slug="demo-form",
        answers={"z": "last", "a": "first"},
    )
    json_payload = canonical_payload_json(payload)
    assert json_payload == (
        '{"event":"submission.accepted","form_id":1,"form_slug":"demo-form","form_version_id":2,'
        '"submission":{"answers":{"a":"first","z":"last"},"created_at":1700000000,"id":3,"submission_seq":4}}'
    )
    assert payload_sha256(json_payload) == payload_sha256(json_payload)
    assert derive_idempotency_key(form_version_id=2, submission_id=3, target_url="https://example.com/hook") == (
        "3dd0cb575702b5a8fd981aca895c871a595b8db327cd28ee695cabb289d1cd1d"
    )


def test_retry_scheduler_backoff_and_deterministic_jitter():
    assert compute_backoff_seconds(base_backoff_seconds=5, attempt_count=0) == 5
    assert compute_backoff_seconds(base_backoff_seconds=5, attempt_count=1) == 10
    assert compute_backoff_seconds(base_backoff_seconds=5, attempt_count=20) == 3600
    jitter_a = deterministic_jitter_seconds(
        payload_sha256="f" * 64,
        attempt_count=3,
        max_jitter_seconds=7,
    )
    jitter_b = deterministic_jitter_seconds(
        payload_sha256="f" * 64,
        attempt_count=3,
        max_jitter_seconds=7,
    )
    assert jitter_a == jitter_b
    assert 0 <= jitter_a <= 7
    assert (
        next_attempt_epoch(
            now_epoch=100,
            base_backoff_seconds=5,
            attempt_count=2,
            payload_sha256="f" * 64,
            max_jitter_seconds=0,
        )
        == 120
    )


def test_rate_limiter_fixed_window_rps():
    limiter = InMemoryRateLimiter()
    with freeze_clock(1700000000):
        limiter.check(key="1.2.3.4", scope="public_submission", limit_rps=2)
        limiter.check(key="1.2.3.4", scope="public_submission", limit_rps=2)
        with pytest.raises(AppError) as exc:
            limiter.check(key="1.2.3.4", scope="public_submission", limit_rps=2)
    assert exc.value.code == "rate_limited"
