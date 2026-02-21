from __future__ import annotations

import json
import os
from typing import Any


def canonical_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def ensure_determinism_env() -> None:
    if os.getenv("PYTHONHASHSEED") != "0":
        raise RuntimeError("Determinism violation: PYTHONHASHSEED must be 0.")


def stable_sorted(seq, key=None):
    return sorted(seq, key=key)
