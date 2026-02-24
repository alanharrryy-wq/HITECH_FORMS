from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any


def canonical_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def ensure_determinism_env() -> None:
    if os.getenv("PYTHONHASHSEED") != "0":
        raise RuntimeError("Determinism violation: PYTHONHASHSEED must be 0.")


_FROZEN_EPOCH: int | None = None
def utc_now_epoch() -> int:
    if _FROZEN_EPOCH is not None:
        return _FROZEN_EPOCH
    fixed_env = os.getenv("HFORMS_FIXED_NOW", "").strip()
    if fixed_env:
        return int(fixed_env)
    return int(datetime.now(timezone.utc).timestamp())


@contextmanager
def freeze_clock(epoch_seconds: int) -> Iterator[None]:
    global _FROZEN_EPOCH
    previous = _FROZEN_EPOCH
    _FROZEN_EPOCH = int(epoch_seconds)
    try:
        yield
    finally:
        _FROZEN_EPOCH = previous


def stable_sorted(seq: list[Any], key: Callable[[Any], Any] | None = None) -> list[Any]:
    if key is None:
        return sorted(seq)
    return sorted(seq, key=key)


def sorted_dict(input_obj: dict[str, Any]) -> dict[str, Any]:
    return {key: input_obj[key] for key in sorted(input_obj)}
