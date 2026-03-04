from __future__ import annotations

import sqlite3
from pathlib import Path

from hitech_forms.ops.db.doctor import EXPECTED_TABLE_COLUMNS, inspect_sqlite_db
from hitech_forms.ops.db.paths import find_repo_root


def _create_table(path: Path, table_name: str, columns: tuple[str, ...]) -> None:
    cols_sql = ", ".join(f'"{column}" TEXT' for column in columns)
    with sqlite3.connect(path) as connection:
        connection.execute(f'CREATE TABLE "{table_name}" ({cols_sql})')
        connection.commit()


def _create_full_head_schema(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        for table_name, columns in EXPECTED_TABLE_COLUMNS.items():
            cols_sql = ", ".join(f'"{column}" TEXT' for column in columns)
            connection.execute(f'CREATE TABLE "{table_name}" ({cols_sql})')
        connection.commit()


def test_doctor_reports_missing_db_file(tmp_path: Path) -> None:
    repo_root = find_repo_root()
    db_path = tmp_path / "missing.db"

    report = inspect_sqlite_db(db_path, repo_root=repo_root)

    assert report.status == "warn"
    assert report.db_exists is False
    assert [issue.code for issue in report.issues] == ["db_file_missing"]
    assert report.recommendations == ("Run: python -m hitech_forms.ops.cli db upgrade",)


def test_doctor_detects_partial_schema_missing_submissions(tmp_path: Path) -> None:
    repo_root = find_repo_root()
    db_path = tmp_path / "partial.db"
    _create_table(db_path, "forms", EXPECTED_TABLE_COLUMNS["forms"])
    _create_table(db_path, "alembic_version", ("version_num",))
    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO alembic_version(version_num) VALUES ('0003_webhook_outbox')")
        connection.commit()

    report = inspect_sqlite_db(db_path, repo_root=repo_root)

    assert report.status == "error"
    assert report.partial_schema is True
    assert "submissions" in report.missing_tables
    assert "Run: HFORMS_ENV=dev python -m hitech_forms.ops.cli db reset --yes-i-know" in report.recommendations
    assert "partial_schema_detected" in [issue.code for issue in report.issues]


def test_doctor_detects_corrupted_sqlite_file(tmp_path: Path) -> None:
    repo_root = find_repo_root()
    db_path = tmp_path / "corrupt.db"
    db_path.write_text("this is not sqlite", encoding="utf-8")

    report = inspect_sqlite_db(db_path, repo_root=repo_root)

    assert report.status == "error"
    assert report.db_exists is True
    assert report.sqlite_corrupted is True
    assert [issue.code for issue in report.issues] == ["db_corrupted"]


def test_doctor_identifies_stamp_head_candidate_when_schema_matches_head(tmp_path: Path) -> None:
    repo_root = find_repo_root()
    db_path = tmp_path / "head_schema_without_version.db"
    _create_full_head_schema(db_path)

    report = inspect_sqlite_db(db_path, repo_root=repo_root)

    assert report.status == "warn"
    assert report.schema_matches_head is True
    assert report.version_matches_head is False
    assert [issue.code for issue in report.issues] == [
        "missing_alembic_version_table",
        "schema_matches_head_but_alembic_version_differs",
    ]
    assert report.recommendations == ("Run: python -m hitech_forms.ops.cli db stamp-head",)
