from __future__ import annotations

import logging
from typing import Any

from hitech_forms.platform.determinism import canonical_json_dumps, sorted_dict, utc_now_epoch
from hitech_forms.platform.request_context import get_request_id, get_startup_seed


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=getattr(logging, level, logging.INFO), format="%(message)s")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = sorted_dict(
        {
            "event": event,
            "request_id": get_request_id() or "-",
            "startup_seed": get_startup_seed(),
            "ts": utc_now_epoch(),
            **fields,
        }
    )
    logger.info(canonical_json_dumps(payload))


def log_security_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = sorted_dict(
        {
            "event": event,
            "request_id": get_request_id() or "-",
            "security": True,
            "startup_seed": get_startup_seed(),
            "ts": utc_now_epoch(),
            **fields,
        }
    )
    logger.warning(canonical_json_dumps(payload))
