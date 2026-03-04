from __future__ import annotations

import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from hitech_forms.ops.cli import app
from hitech_forms.ops.db.doctor import EXPECTED_TABLE_COLUMNS
from hitech_forms.platform.settings import reset_settings_cache

runner = CliRunner()


def _create_partial_schema_missing_submissions(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        for table_name in ("forms", "form_versions", "fields", "answers"):
            cols_sql = ", ".join(f'"{column}" TEXT' for column in EXPECTED_TABLE_COLUMNS[table_name])
            connection.execute(f'CREATE TABLE "{table_name}" ({cols_sql})')
        connection.execute('CREATE TABLE "alembic_version" ("version_num" TEXT)')
        connection.execute("INSERT INTO alembic_version(version_num) VALUES ('0003_webhook_outbox')")
        connection.commit()


def test_doctor_recommends_reset_for_partial_schema_missing_submissions(
    tmp_path: Path, monkeypatch
) -> None:
    db_path = tmp_path / "legacy_partial.db"
    _create_partial_schema_missing_submissions(db_path)

    monkeypatch.setenv("HFORMS_DB_PATH", str(db_path))
    monkeypatch.setenv("HFORMS_ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("HFORMS_TIMEZONE", "UTC")
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    reset_settings_cache()

    result = runner.invoke(app, ["db", "doctor"])

    assert result.exit_code == 0
    assert "partial_schema_detected" in result.output
    assert "db reset --yes-i-know" in result.output
