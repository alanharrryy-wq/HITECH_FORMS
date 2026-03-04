from __future__ import annotations

import sqlite3
from pathlib import Path

from hitech_forms.ops.db.recovery import create_backup, is_reset_allowed


def _create_sqlite_db(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")
        connection.commit()


def test_create_backup_uses_monotonic_sequence_names(tmp_path: Path) -> None:
    db_path = tmp_path / "source.db"
    backup_dir = tmp_path / "backups"
    _create_sqlite_db(db_path)

    first = create_backup(db_path=db_path, backup_dir=backup_dir)
    second = create_backup(db_path=db_path, backup_dir=backup_dir)

    assert Path(first.backup_path).name == "backup_001.db"
    assert Path(second.backup_path).name == "backup_002.db"


def test_is_reset_allowed_dev_or_override_only() -> None:
    assert is_reset_allowed({"HFORMS_ENV": "dev"}) is True
    assert is_reset_allowed({"HFORMS_ALLOW_DB_RESET": "1"}) is True
    assert is_reset_allowed({"HFORMS_ENV": "prod", "HFORMS_ALLOW_DB_RESET": "0"}) is False
