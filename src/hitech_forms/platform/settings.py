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
    feature_demo: bool
    feature_webhooks_outbox: bool
    feature_rate_limit: bool
    feature_metrics: bool
    webhook_target_url: str
    webhook_max_attempts: int
    webhook_base_backoff_seconds: int
    webhook_jitter: int
    rate_limit_rps_public: int
    rate_limit_rps_admin: int


_SETTINGS: Settings | None = None


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default)).strip()
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer for {name}: {value}") from exc


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"Invalid boolean for {name}: {value}")


def _load_settings() -> Settings:
    return Settings(
        db_path=os.getenv("HFORMS_DB_PATH", "var/hitech_forms.db").strip(),
        host=os.getenv("HFORMS_HOST", "127.0.0.1").strip(),
        port=_env_int("HFORMS_PORT", 8000),
        admin_token=os.getenv("HFORMS_ADMIN_TOKEN", "").strip(),
        timezone=os.getenv("HFORMS_TIMEZONE", "UTC").strip().upper(),
        rate_limit_per_minute=_env_int("HFORMS_RATE_LIMIT_PER_MINUTE", 300),
        log_level=os.getenv("HFORMS_LOG_LEVEL", "INFO").strip().upper(),
        feature_demo=_env_bool("HFORMS_FLAG_DEMO", False),
        feature_webhooks_outbox=_env_bool("HFORMS_FEATURE_WEBHOOKS_OUTBOX", False),
        feature_rate_limit=_env_bool("HFORMS_FEATURE_RATE_LIMIT", False),
        feature_metrics=_env_bool("HFORMS_FEATURE_METRICS", False),
        webhook_target_url=os.getenv("HFORMS_WEBHOOK_TARGET_URL", "").strip(),
        webhook_max_attempts=_env_int("HFORMS_WEBHOOK_MAX_ATTEMPTS", 8),
        webhook_base_backoff_seconds=_env_int("HFORMS_WEBHOOK_BASE_BACKOFF_SECONDS", 5),
        webhook_jitter=_env_int("HFORMS_WEBHOOK_JITTER", 0),
        rate_limit_rps_public=_env_int("HFORMS_RATE_LIMIT_RPS_PUBLIC", 0),
        rate_limit_rps_admin=_env_int("HFORMS_RATE_LIMIT_RPS_ADMIN", 0),
    )


def validate_settings(settings: Settings) -> None:
    if not settings.admin_token:
        raise RuntimeError("HFORMS_ADMIN_TOKEN is required.")
    if settings.timezone != "UTC":
        raise RuntimeError("HFORMS_TIMEZONE must be UTC for deterministic behavior.")
    db_parent = Path(settings.db_path).resolve().parent
    db_parent.mkdir(parents=True, exist_ok=True)
    if settings.rate_limit_per_minute < 0:
        raise RuntimeError("HFORMS_RATE_LIMIT_PER_MINUTE must be >= 0.")
    if settings.webhook_max_attempts < 1:
        raise RuntimeError("HFORMS_WEBHOOK_MAX_ATTEMPTS must be >= 1.")
    if settings.webhook_base_backoff_seconds < 1:
        raise RuntimeError("HFORMS_WEBHOOK_BASE_BACKOFF_SECONDS must be >= 1.")
    if settings.webhook_jitter < 0:
        raise RuntimeError("HFORMS_WEBHOOK_JITTER must be >= 0.")
    if settings.rate_limit_rps_public < 0:
        raise RuntimeError("HFORMS_RATE_LIMIT_RPS_PUBLIC must be >= 0.")
    if settings.rate_limit_rps_admin < 0:
        raise RuntimeError("HFORMS_RATE_LIMIT_RPS_ADMIN must be >= 0.")


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
