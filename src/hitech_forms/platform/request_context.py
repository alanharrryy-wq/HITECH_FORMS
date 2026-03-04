from __future__ import annotations

import hashlib
from contextvars import ContextVar, Token
from threading import Lock

_REQUEST_ID: ContextVar[str] = ContextVar("hforms_request_id", default="")
_COUNTER_LOCK = Lock()
_REQUEST_COUNTER = 0
_STARTUP_SEED = "seed0000"


def set_startup_seed(seed: str) -> None:
    global _STARTUP_SEED
    _STARTUP_SEED = seed[:24] or "seed0000"


def get_startup_seed() -> str:
    return _STARTUP_SEED


def sanitize_request_id(value: str) -> str:
    cleaned = "".join(ch for ch in value.strip() if ch.isalnum() or ch in {"-", "_", "."})
    return cleaned[:120]


def build_deterministic_request_id(method: str, path: str) -> str:
    global _REQUEST_COUNTER
    with _COUNTER_LOCK:
        _REQUEST_COUNTER += 1
        count = _REQUEST_COUNTER
    route_hash = hashlib.sha256(f"{method}:{path}".encode()).hexdigest()[:8]
    return f"{_STARTUP_SEED}-{count:08d}-{route_hash}"


def bind_request_id(request_id: str) -> Token[str]:
    return _REQUEST_ID.set(request_id)


def reset_request_id(token: Token[str]) -> None:
    _REQUEST_ID.reset(token)


def get_request_id() -> str | None:
    value = _REQUEST_ID.get()
    return value or None


def reset_request_context() -> None:
    global _REQUEST_COUNTER
    with _COUNTER_LOCK:
        _REQUEST_COUNTER = 0
