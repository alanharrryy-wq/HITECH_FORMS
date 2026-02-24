from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run_alembic_upgrade(db_path: Path) -> None:
    env = os.environ.copy()
    env["HFORMS_DB_PATH"] = str(db_path)
    env.setdefault("HFORMS_ADMIN_TOKEN", "test-admin-token")
    env.setdefault("HFORMS_TIMEZONE", "UTC")
    env.setdefault("PYTHONHASHSEED", "0")
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "migrations/alembic.ini", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def runtime_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    db_path = tmp_path / "hitech_forms_test.db"
    monkeypatch.setenv("HFORMS_DB_PATH", str(db_path))
    monkeypatch.setenv("HFORMS_HOST", "127.0.0.1")
    monkeypatch.setenv("HFORMS_PORT", "8000")
    monkeypatch.setenv("HFORMS_ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("HFORMS_TIMEZONE", "UTC")
    monkeypatch.setenv("HFORMS_RATE_LIMIT_PER_MINUTE", "999999")
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    monkeypatch.setenv("HFORMS_FIXED_NOW", "1700000000")
    _run_alembic_upgrade(db_path)

    from hitech_forms.db.engine import reset_engine_cache
    from hitech_forms.platform.settings import reset_settings_cache

    reset_settings_cache()
    reset_engine_cache()
    return {"db_path": str(db_path), "admin_token": "test-admin-token"}


@pytest.fixture()
async def client(runtime_env: dict[str, str]) -> AsyncIterator[httpx.AsyncClient]:
    _ = runtime_env
    from hitech_forms.app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
