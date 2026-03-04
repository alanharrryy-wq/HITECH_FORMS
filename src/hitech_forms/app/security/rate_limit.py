from __future__ import annotations

from collections import defaultdict
from threading import Lock

from hitech_forms.platform.determinism import utc_now_epoch
from hitech_forms.platform.errors import rate_limited


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[tuple[str, str, int], int] = defaultdict(int)
        self._lock = Lock()

    def check(self, *, key: str, scope: str, limit_rps: int) -> None:
        if limit_rps <= 0:
            return
        second_bucket = utc_now_epoch()
        bucket_key = (scope, key, second_bucket)
        with self._lock:
            self._cleanup(second_bucket)
            self._buckets[bucket_key] += 1
            count = self._buckets[bucket_key]
        if count > limit_rps:
            raise rate_limited(
                details={
                    "scope": scope,
                    "limit_rps": limit_rps,
                    "bucket_epoch": second_bucket,
                }
            )

    def _cleanup(self, second_bucket: int) -> None:
        stale_keys = [key for key in self._buckets if key[2] < second_bucket - 1]
        for stale_key in stale_keys:
            self._buckets.pop(stale_key, None)

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
