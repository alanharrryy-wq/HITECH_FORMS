from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hitech_forms.ops.db.alembic import AlembicCommandError, run_alembic_command
from hitech_forms.ops.db.doctor import DoctorReport, inspect_sqlite_db
from hitech_forms.ops.db.paths import DEFAULT_DB_RELATIVE_PATH, resolve_repo_path
from hitech_forms.platform.determinism import canonical_json_dumps, utc_now_epoch

BACKUP_PATTERN = re.compile(r"^backup_(\d+)(?:_ts_\d+)?\.db$")
RESET_RUN_PATTERN = re.compile(r"^run-(\d{4})$")


@dataclass(frozen=True)
class BackupResult:
    source_db_path: str
    backup_path: str


@dataclass(frozen=True)
class ResetResult:
    db_path: str
    default_db_path: str
    run_dir: str
    removed_existing_db: bool
    before_status: str
    after_status: str


@dataclass(frozen=True)
class StampResult:
    db_path: str
    stamped: bool
    reason: str
    before_status: str
    after_status: str


def _next_backup_index(backup_dir: Path) -> int:
    existing: list[int] = []
    if backup_dir.exists():
        for child in backup_dir.iterdir():
            if not child.is_file():
                continue
            match = BACKUP_PATTERN.match(child.name)
            if match:
                existing.append(int(match.group(1)))
    return (max(existing) if existing else 0) + 1


def _next_reset_run_name(root: Path) -> str:
    existing: list[int] = []
    if root.exists():
        for child in root.iterdir():
            if not child.is_dir():
                continue
            match = RESET_RUN_PATTERN.match(child.name)
            if match:
                existing.append(int(match.group(1)))
    next_id = (max(existing) if existing else 0) + 1
    return f"run-{next_id:04d}"


def _write_canonical_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(canonical_json_dumps(payload) + "\n", encoding="utf-8")


def _append_event(path: Path, event: str, **fields: Any) -> None:
    payload = {"event": event, "ts": utc_now_epoch(), **fields}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json_dumps(payload))
        handle.write("\n")


def create_backup(*, db_path: Path, backup_dir: Path, with_timestamp: bool = False) -> BackupResult:
    if not db_path.exists():
        raise RuntimeError(f"Database file does not exist: {db_path}")
    if not db_path.is_file():
        raise RuntimeError(f"Database path is not a file: {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    next_index = _next_backup_index(backup_dir)
    backup_name = f"backup_{next_index:03d}.db"
    if with_timestamp:
        backup_name = f"backup_{next_index:03d}_ts_{utc_now_epoch()}.db"
    destination = (backup_dir / backup_name).resolve()
    shutil.copyfile(db_path, destination)
    return BackupResult(source_db_path=str(db_path), backup_path=str(destination))


def upgrade_to_head(*, repo_root: Path, db_path: Path) -> None:
    run_alembic_command(repo_root=repo_root, db_path=db_path, args=("upgrade", "head"))


def format_upgrade_failure(*, error: AlembicCommandError, db_path: Path) -> str:
    stderr = error.stderr.strip()
    stdout = error.stdout.strip()
    detail_blob = stderr or stdout
    detail_line = ""
    if detail_blob:
        lines = [line.strip() for line in detail_blob.splitlines() if line.strip()]
        preferred_tokens = ("no such table", "operationalerror", "sqlite3.", "sqlalchemy.exc")
        for token in preferred_tokens:
            matched = next((line for line in lines if token in line.lower()), "")
            if matched:
                detail_line = matched
                break
        if not detail_line and lines:
            detail_line = lines[-1]
    lower_blob = detail_blob.lower()
    is_sqlite_error = "sqlite" in lower_blob or "no such table" in lower_blob or "database" in lower_blob

    lines = [
        f"db upgrade failed for database path: {db_path}",
    ]
    if detail_line:
        lines.append(f"Alembic detail: {detail_line}")
    if is_sqlite_error:
        lines.append("Detected SQLite migration/preflight issue.")
    lines.extend(
        [
            "Run: python -m hitech_forms.ops.cli db doctor",
            "Recommended next steps:",
            "1. python -m hitech_forms.ops.cli db doctor",
            "2. python -m hitech_forms.ops.cli db backup",
            "3. HFORMS_ENV=dev python -m hitech_forms.ops.cli db reset --yes-i-know",
        ]
    )
    return "\n".join(lines)


def is_reset_allowed(env: dict[str, str] | None = None) -> bool:
    source = env if env is not None else dict(os.environ)
    env_name = source.get("HFORMS_ENV", "").strip().lower()
    allow_override = source.get("HFORMS_ALLOW_DB_RESET", "").strip() == "1"
    return env_name == "dev" or allow_override


def reset_sqlite_db(
    *,
    repo_root: Path,
    db_path: Path,
    yes_i_know: bool,
    env: dict[str, str] | None = None,
) -> ResetResult:
    source_env = env if env is not None else dict(os.environ)
    if not yes_i_know:
        raise RuntimeError("Refusing to reset DB without --yes-i-know.")
    if not is_reset_allowed(source_env):
        raise RuntimeError("Reset blocked. Requires HFORMS_ENV=dev or HFORMS_ALLOW_DB_RESET=1.")

    default_db_path = resolve_repo_path(DEFAULT_DB_RELATIVE_PATH, repo_root)
    allow_override = source_env.get("HFORMS_ALLOW_DB_RESET", "").strip() == "1"
    if db_path.resolve() != default_db_path and not allow_override:
        raise RuntimeError(
            "Reset is restricted to default DB path unless HFORMS_ALLOW_DB_RESET=1 is explicitly set."
        )

    runs_root = resolve_repo_path(Path("var/db_reset_runs"), repo_root)
    runs_root.mkdir(parents=True, exist_ok=True)
    run_dir = (runs_root / _next_reset_run_name(runs_root)).resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    event_log_path = run_dir / "events.jsonl"

    before_report = inspect_sqlite_db(db_path, repo_root=repo_root)
    _write_canonical_json(run_dir / "doctor_before.json", before_report.to_dict())
    _append_event(event_log_path, "doctor_before", status=before_report.status)

    removed_existing_db = False
    if db_path.exists():
        shutil.copyfile(db_path, run_dir / "db_before_reset.db")
        db_path.unlink()
        removed_existing_db = True
        _append_event(event_log_path, "db_file_deleted", db_path=str(db_path))
    else:
        _append_event(event_log_path, "db_file_not_found", db_path=str(db_path))

    db_path.parent.mkdir(parents=True, exist_ok=True)
    upgrade_to_head(repo_root=repo_root, db_path=db_path)
    _append_event(event_log_path, "alembic_upgrade_head", db_path=str(db_path))

    after_report = inspect_sqlite_db(db_path, repo_root=repo_root)
    _write_canonical_json(run_dir / "doctor_after.json", after_report.to_dict())
    _append_event(event_log_path, "doctor_after", status=after_report.status)

    summary_db_path = str(db_path)
    summary_default_db_path = str(default_db_path)
    summary_run_dir = str(run_dir)
    summary_before_status = before_report.status
    summary_after_status = after_report.status
    summary = {
        "db_path": summary_db_path,
        "default_db_path": summary_default_db_path,
        "run_dir": summary_run_dir,
        "removed_existing_db": removed_existing_db,
        "before_status": summary_before_status,
        "after_status": summary_after_status,
    }
    _write_canonical_json(run_dir / "summary.json", summary)
    return ResetResult(
        db_path=summary_db_path,
        default_db_path=summary_default_db_path,
        run_dir=summary_run_dir,
        removed_existing_db=removed_existing_db,
        before_status=summary_before_status,
        after_status=summary_after_status,
    )


def stamp_head_strict(*, repo_root: Path, db_path: Path) -> StampResult:
    before_report = inspect_sqlite_db(db_path, repo_root=repo_root)
    if not before_report.db_exists:
        raise RuntimeError("Cannot stamp head: database file does not exist.")
    if not before_report.sqlite_readable or before_report.sqlite_corrupted:
        raise RuntimeError("Cannot stamp head: database is unreadable or corrupted.")
    if not before_report.schema_matches_head:
        raise RuntimeError(
            "Cannot stamp head: schema does not match expected head state. "
            "Run db doctor and recover via reset/upgrade."
        )

    if before_report.version_matches_head:
        return StampResult(
            db_path=str(db_path),
            stamped=False,
            reason="already_at_head",
            before_status=before_report.status,
            after_status=before_report.status,
        )

    run_alembic_command(repo_root=repo_root, db_path=db_path, args=("stamp", "head"))
    after_report = inspect_sqlite_db(db_path, repo_root=repo_root)
    if not after_report.version_matches_head:
        raise RuntimeError("Stamp head completed but alembic_version is still not at head.")
    return StampResult(
        db_path=str(db_path),
        stamped=True,
        reason="stamped_head",
        before_status=before_report.status,
        after_status=after_report.status,
    )


def summarize_report(report: DoctorReport) -> dict[str, Any]:
    return {
        "status": report.status,
        "db_exists": report.db_exists,
        "sqlite_readable": report.sqlite_readable,
        "sqlite_corrupted": report.sqlite_corrupted,
        "partial_schema": report.partial_schema,
        "schema_matches_head": report.schema_matches_head,
        "version_matches_head": report.version_matches_head,
        "missing_tables": list(report.missing_tables),
        "recommendations": list(report.recommendations),
    }
