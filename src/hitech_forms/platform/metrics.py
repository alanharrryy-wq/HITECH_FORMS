from __future__ import annotations

from collections import defaultdict
from threading import Lock

_METRICS_LOCK = Lock()
_COUNTERS: dict[str, int] = defaultdict(int)
_GAUGES: dict[str, int] = {}


def increment_counter(name: str, amount: int = 1) -> None:
    with _METRICS_LOCK:
        _COUNTERS[name] = int(_COUNTERS.get(name, 0)) + int(amount)


def set_gauge(name: str, value: int) -> None:
    with _METRICS_LOCK:
        _GAUGES[name] = int(value)


def snapshot_metrics() -> dict[str, int]:
    with _METRICS_LOCK:
        merged: dict[str, int] = {}
        merged.update(_COUNTERS)
        merged.update(_GAUGES)
    return {key: merged[key] for key in sorted(merged)}


def reset_metrics() -> None:
    with _METRICS_LOCK:
        _COUNTERS.clear()
        _GAUGES.clear()


def render_text_metrics(metrics: dict[str, int]) -> str:
    lines = [f"{key} {metrics[key]}" for key in sorted(metrics)]
    return "\n".join(lines) + ("\n" if lines else "")
