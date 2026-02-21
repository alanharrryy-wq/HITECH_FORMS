from __future__ import annotations

from sqlalchemy import create_engine

from hitech_forms.platform.settings import get_settings

_ENGINE = None


def get_engine():
    global _ENGINE
    if _ENGINE is None:
        s = get_settings()
        url = f"sqlite:///{s.db_path}"
        _ENGINE = create_engine(
            url, future=True, echo=False, connect_args={"check_same_thread": False}
        )
    return _ENGINE
