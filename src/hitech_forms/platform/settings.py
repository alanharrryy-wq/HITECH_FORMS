from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_path: str = os.getenv("HFORMS_DB_PATH", "var/hitech_forms.db")
    host: str = os.getenv("HFORMS_HOST", "127.0.0.1")
    port: int = int(os.getenv("HFORMS_PORT", "8000"))


_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings()
    return _SETTINGS
