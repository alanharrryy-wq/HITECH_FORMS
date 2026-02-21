from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name, str(default)).strip().lower()
    return v in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class FeatureFlags:
    demo: bool = _env_bool("HFORMS_FLAG_DEMO", False)


_FLAGS: FeatureFlags | None = None


def get_feature_flags() -> FeatureFlags:
    global _FLAGS
    if _FLAGS is None:
        _FLAGS = FeatureFlags()
    return _FLAGS
