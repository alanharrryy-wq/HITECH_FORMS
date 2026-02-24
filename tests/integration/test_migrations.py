from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[2]


def _run_alembic(*args: str, env: dict[str, str]) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "migrations/alembic.ini", *args],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def test_migration_replay_and_reflection(runtime_env):
    env = os.environ.copy()
    env["HFORMS_DB_PATH"] = runtime_env["db_path"]
    env["HFORMS_ADMIN_TOKEN"] = runtime_env["admin_token"]
    env["HFORMS_TIMEZONE"] = "UTC"
    env["PYTHONHASHSEED"] = "0"

    _run_alembic("upgrade", "head", env=env)
    _run_alembic("upgrade", "head", env=env)
    _run_alembic("downgrade", "base", env=env)
    _run_alembic("upgrade", "head", env=env)

    engine = create_engine(f"sqlite:///{runtime_env['db_path']}")
    inspector = inspect(engine)

    table_names = set(inspector.get_table_names())
    assert table_names == {
        "alembic_version",
        "forms",
        "form_versions",
        "fields",
        "submissions",
        "answers",
    }

    forms_indexes = {index["name"] for index in inspector.get_indexes("forms")}
    assert "ix_forms_slug" in forms_indexes
    assert "ix_forms_created_at" in forms_indexes
