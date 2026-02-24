from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from hitech_forms.platform.settings import get_settings

_ENGINE: Engine | None = None


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        s = get_settings()
        url = f"sqlite:///{s.db_path}"
        _ENGINE = create_engine(
            url, future=True, echo=False, connect_args={"check_same_thread": False}
        )
        if url.startswith("sqlite"):
            event.listen(_ENGINE, "connect", _enable_sqlite_fk)
    return _ENGINE


def _enable_sqlite_fk(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def reset_engine_cache() -> None:
    global _ENGINE
    if _ENGINE is not None:
        _ENGINE.dispose()
    _ENGINE = None
