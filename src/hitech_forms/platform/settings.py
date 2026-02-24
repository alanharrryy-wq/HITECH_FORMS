from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: str
    host: str
    port: int
    admin_token: str
    timezone: str
    rate_limit_per_minute: int
    log_level: str


_SETTINGS: Settings | None = None


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default)).strip()
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer for {name}: {value}") from exc


def _load_settings() -> Settings:
    return Settings(
        db_path=os.getenv("HFORMS_DB_PATH", "var/hitech_forms.db").strip(),
        host=os.getenv("HFORMS_HOST", "127.0.0.1").strip(),
        port=_env_int("HFORMS_PORT", 8000),
        admin_token=os.getenv("HFORMS_ADMIN_TOKEN", "").strip(),
        timezone=os.getenv("HFORMS_TIMEZONE", "UTC").strip().upper(),
        rate_limit_per_minute=_env_int("HFORMS_RATE_LIMIT_PER_MINUTE", 300),
        log_level=os.getenv("HFORMS_LOG_LEVEL", "INFO").strip().upper(),
    )


def validate_settings(settings: Settings) -> None:
    if not settings.admin_token:
        raise RuntimeError("HFORMS_ADMIN_TOKEN is required.")
    if settings.timezone != "UTC":
        raise RuntimeError("HFORMS_TIMEZONE must be UTC for deterministic behavior.")
    db_parent = Path(settings.db_path).resolve().parent
    db_parent.mkdir(parents=True, exist_ok=True)
    if settings.rate_limit_per_minute < 1:
        raise RuntimeError("HFORMS_RATE_LIMIT_PER_MINUTE must be >= 1.")


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        loaded = _load_settings()
        validate_settings(loaded)
        _SETTINGS = loaded
    return _SETTINGS


def reset_settings_cache() -> None:
    global _SETTINGS
    _SETTINGS = None
