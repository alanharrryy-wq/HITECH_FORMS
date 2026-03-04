from __future__ import annotations

import hashlib

MAX_BACKOFF_SECONDS = 3600


def compute_backoff_seconds(*, base_backoff_seconds: int, attempt_count: int) -> int:
    backoff = int(base_backoff_seconds * (2**attempt_count))
    if backoff > MAX_BACKOFF_SECONDS:
        return MAX_BACKOFF_SECONDS
    return backoff


def deterministic_jitter_seconds(
    *,
    payload_sha256: str,
    attempt_count: int,
    max_jitter_seconds: int,
) -> int:
    if max_jitter_seconds <= 0:
        return 0
    digest = hashlib.sha256(f"{payload_sha256}:{attempt_count}".encode()).hexdigest()
    return int(digest[:8], 16) % (max_jitter_seconds + 1)


def next_attempt_epoch(
    *,
    now_epoch: int,
    base_backoff_seconds: int,
    attempt_count: int,
    payload_sha256: str,
    max_jitter_seconds: int,
) -> int:
    backoff = compute_backoff_seconds(
        base_backoff_seconds=base_backoff_seconds,
        attempt_count=attempt_count,
    )
    jitter = deterministic_jitter_seconds(
        payload_sha256=payload_sha256,
        attempt_count=attempt_count,
        max_jitter_seconds=max_jitter_seconds,
    )
    return now_epoch + backoff + jitter
