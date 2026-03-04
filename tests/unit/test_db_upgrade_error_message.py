from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hitech_forms.ops.cli import app
from hitech_forms.ops.db.alembic import AlembicCommandError
from hitech_forms.platform.settings import reset_settings_cache

runner = CliRunner()


def test_db_upgrade_reports_helpful_doctor_message_on_sqlite_failure(
    tmp_path: Path, monkeypatch
) -> None:
    db_path = tmp_path / "legacy.db"

    def _raise_alembic_error(*, repo_root, db_path):  # type: ignore[no-untyped-def]
        _ = (repo_root, db_path)
        raise AlembicCommandError(
            command=["python", "-m", "alembic", "upgrade", "head"],
            return_code=1,
            stdout="",
            stderr="sqlite3.OperationalError: no such table: submissions",
        )

    monkeypatch.setattr("hitech_forms.ops.cli.upgrade_to_head", _raise_alembic_error)
    monkeypatch.setenv("HFORMS_DB_PATH", str(db_path))
    monkeypatch.setenv("HFORMS_ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("HFORMS_TIMEZONE", "UTC")
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    reset_settings_cache()

    result = runner.invoke(app, ["db", "upgrade"])

    assert result.exit_code == 1
    assert "db upgrade failed for database path" in result.output
    assert "Run: python -m hitech_forms.ops.cli db doctor" in result.output
    assert "Traceback" not in result.output
