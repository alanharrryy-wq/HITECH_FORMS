from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from hitech_forms.platform.errors import rate_limited


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[tuple[str, str, int], int] = defaultdict(int)

    def check(self, *, key: str, scope: str, limit_per_minute: int) -> None:
        minute_bucket = int(datetime.now(timezone.utc).timestamp()) // 60
        bucket_key = (scope, key, minute_bucket)
        self._buckets[bucket_key] += 1
        if self._buckets[bucket_key] > limit_per_minute:
            raise rate_limited()
