from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory

from hitech_forms.ops.db.paths import DEFAULT_DB_RELATIVE_PATH, find_repo_root, resolve_repo_path

CORE_TABLES: tuple[str, ...] = (
    "forms",
    "form_versions",
    "fields",
    "submissions",
    "answers",
)

EXPECTED_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "forms": ("id", "title", "slug", "status", "active_version_id", "created_at", "updated_at"),
    "form_versions": ("id", "form_id", "version_number", "status", "created_at", "published_at"),
    "fields": (
        "form_version_id",
        "id",
        "field_key",
        "label",
        "type",
        "required",
        "position",
        "config_json",
        "created_at",
    ),
    "submissions": ("id", "form_id", "form_version_id", "created_at", "submission_seq"),
    "answers": ("id", "submission_id", "field_key", "value_text", "created_at"),
    "webhook_outbox": (
        "id",
        "created_at",
        "next_attempt_at",
        "attempt_count",
        "status",
        "target_url",
        "payload_json",
        "payload_sha256",
        "idempotency_key",
        "form_id",
        "form_version_id",
        "submission_id",
        "last_error",
        "delivered_at",
    ),
    "webhook_delivery_log": (
        "id",
        "outbox_id",
        "attempt_no",
        "attempted_at",
        "http_status",
        "response_snippet",
        "error_type",
        "error_message",
    ),
}
EXPECTED_TABLES: tuple[str, ...] = tuple(EXPECTED_TABLE_COLUMNS.keys())


@dataclass(frozen=True)
class TableMismatch:
    table: str
    missing_columns: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "missing_columns": list(self.missing_columns),
        }


@dataclass(frozen=True)
class DriftIssue:
    code: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "severity": self.severity, "message": self.message}


@dataclass(frozen=True)
class AlembicCheck:
    table_exists: bool
    versions: tuple[str, ...]
    version_matches_head: bool


@dataclass(frozen=True)
class ExpectedTablesCheck:
    missing_tables: tuple[str, ...]
    missing_core_tables: tuple[str, ...]
    partial_schema: bool
    table_mismatches: tuple[TableMismatch, ...]
    schema_matches_head: bool


@dataclass(frozen=True)
class DoctorReport:
    db_path_input: str
    db_path_resolved: str
    default_db_path: str
    db_exists: bool
    sqlite_readable: bool
    sqlite_corrupted: bool
    error: str | None
    alembic_head: str
    alembic_version_table_exists: bool
    alembic_versions: tuple[str, ...]
    tables_present: tuple[str, ...]
    expected_tables: tuple[str, ...]
    missing_tables: tuple[str, ...]
    missing_core_tables: tuple[str, ...]
    partial_schema: bool
    table_mismatches: tuple[TableMismatch, ...]
    schema_matches_head: bool
    version_matches_head: bool
    issues: tuple[DriftIssue, ...]
    recommendations: tuple[str, ...]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "db_path_input": self.db_path_input,
            "db_path_resolved": self.db_path_resolved,
            "default_db_path": self.default_db_path,
            "db_exists": self.db_exists,
            "sqlite_readable": self.sqlite_readable,
            "sqlite_corrupted": self.sqlite_corrupted,
            "error": self.error,
            "alembic_head": self.alembic_head,
            "alembic_version_table_exists": self.alembic_version_table_exists,
            "alembic_versions": list(self.alembic_versions),
            "tables_present": list(self.tables_present),
            "expected_tables": list(self.expected_tables),
            "missing_tables": list(self.missing_tables),
            "missing_core_tables": list(self.missing_core_tables),
            "partial_schema": self.partial_schema,
            "table_mismatches": [item.to_dict() for item in self.table_mismatches],
            "schema_matches_head": self.schema_matches_head,
            "version_matches_head": self.version_matches_head,
            "issues": [issue.to_dict() for issue in self.issues],
            "recommendations": list(self.recommendations),
        }


def open_db(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(str(path))


def list_tables(connection: sqlite3.Connection) -> tuple[str, ...]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name ASC"
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _list_columns(connection: sqlite3.Connection, table_name: str) -> tuple[str, ...]:
    rows = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return tuple(sorted(str(row[1]) for row in rows))


def check_alembic_version(
    connection: sqlite3.Connection,
    *,
    table_names: tuple[str, ...],
    alembic_head: str,
) -> AlembicCheck:
    table_exists = "alembic_version" in table_names
    if not table_exists:
        return AlembicCheck(table_exists=False, versions=(), version_matches_head=False)
    rows = connection.execute(
        "SELECT version_num FROM alembic_version ORDER BY version_num ASC"
    ).fetchall()
    versions = tuple(str(row[0]) for row in rows if row and row[0] is not None)
    version_matches_head = len(versions) == 1 and versions[0] == alembic_head
    return AlembicCheck(
        table_exists=table_exists,
        versions=versions,
        version_matches_head=version_matches_head,
    )


def check_expected_tables(
    connection: sqlite3.Connection,
    *,
    table_names: tuple[str, ...],
) -> ExpectedTablesCheck:
    present_set = set(table_names)
    missing_tables = tuple(table for table in EXPECTED_TABLES if table not in present_set)
    missing_core_tables = tuple(table for table in CORE_TABLES if table not in present_set)
    present_expected_tables = tuple(table for table in EXPECTED_TABLES if table in present_set)
    partial_schema = bool(present_expected_tables) and bool(missing_tables)

    mismatches: list[TableMismatch] = []
    for table_name in present_expected_tables:
        columns = set(_list_columns(connection, table_name))
        missing_columns = tuple(
            column for column in EXPECTED_TABLE_COLUMNS[table_name] if column not in columns
        )
        if missing_columns:
            mismatches.append(TableMismatch(table=table_name, missing_columns=missing_columns))

    table_mismatches = tuple(mismatches)
    schema_matches_head = not missing_tables and not table_mismatches
    return ExpectedTablesCheck(
        missing_tables=missing_tables,
        missing_core_tables=missing_core_tables,
        partial_schema=partial_schema,
        table_mismatches=table_mismatches,
        schema_matches_head=schema_matches_head,
    )


def detect_drift_scenarios(
    *,
    db_exists: bool,
    sqlite_readable: bool,
    sqlite_corrupted: bool,
    error: str | None,
    alembic_version_table_exists: bool,
    alembic_versions: tuple[str, ...],
    missing_tables: tuple[str, ...],
    partial_schema: bool,
    table_mismatches: tuple[TableMismatch, ...],
    schema_matches_head: bool,
    version_matches_head: bool,
) -> tuple[DriftIssue, ...]:
    issues: list[DriftIssue] = []
    if not db_exists:
        issues.append(
            DriftIssue(
                code="db_file_missing",
                severity="warn",
                message="Database file does not exist yet.",
            )
        )
        return tuple(issues)

    if sqlite_corrupted:
        issues.append(
            DriftIssue(
                code="db_corrupted",
                severity="error",
                message=error or "SQLite quick_check failed.",
            )
        )
        return tuple(issues)

    if not sqlite_readable:
        issues.append(
            DriftIssue(
                code="db_unreadable",
                severity="error",
                message=error or "Database file exists but could not be opened.",
            )
        )
        return tuple(issues)

    if not alembic_version_table_exists:
        issues.append(
            DriftIssue(
                code="missing_alembic_version_table",
                severity="warn",
                message="alembic_version table is missing.",
            )
        )

    if missing_tables:
        issues.append(
            DriftIssue(
                code="missing_expected_tables",
                severity="error",
                message=f"Missing expected tables: {', '.join(missing_tables)}",
            )
        )

    if partial_schema:
        issues.append(
            DriftIssue(
                code="partial_schema_detected",
                severity="error",
                message="Only part of the expected schema is present.",
            )
        )

    if table_mismatches:
        issues.append(
            DriftIssue(
                code="table_column_mismatch",
                severity="error",
                message="One or more tables are missing required columns.",
            )
        )

    if alembic_version_table_exists and not version_matches_head:
        version_label = ", ".join(alembic_versions) if alembic_versions else "<none>"
        issues.append(
            DriftIssue(
                code="alembic_head_mismatch",
                severity="warn",
                message=f"alembic_version is not at head: {version_label}",
            )
        )

    if version_matches_head and not schema_matches_head:
        issues.append(
            DriftIssue(
                code="alembic_claims_head_but_schema_differs",
                severity="error",
                message="alembic_version reports head but schema does not match expected head state.",
            )
        )

    if schema_matches_head and not version_matches_head:
        issues.append(
            DriftIssue(
                code="schema_matches_head_but_alembic_version_differs",
                severity="warn",
                message="Schema matches head but alembic_version is missing or mismatched.",
            )
        )

    return tuple(issues)


def _dedupe_keep_order(items: list[str]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        deduped.append(item)
        seen.add(item)
    return tuple(deduped)


def _build_recommendations(report: DoctorReport) -> tuple[str, ...]:
    actions: list[str] = []
    if not report.db_exists:
        actions.append("Run: python -m hitech_forms.ops.cli db upgrade")
        return tuple(actions)

    if not report.sqlite_readable or report.sqlite_corrupted:
        actions.append("Run: python -m hitech_forms.ops.cli db backup")
        actions.append("Run: HFORMS_ENV=dev python -m hitech_forms.ops.cli db reset --yes-i-know")
        return _dedupe_keep_order(actions)

    if report.partial_schema or report.missing_core_tables:
        actions.append("Run: python -m hitech_forms.ops.cli db backup")
        actions.append("Run: HFORMS_ENV=dev python -m hitech_forms.ops.cli db reset --yes-i-know")

    if report.schema_matches_head and not report.version_matches_head:
        actions.append("Run: python -m hitech_forms.ops.cli db stamp-head")

    if report.missing_tables and not report.partial_schema:
        actions.append("Run: python -m hitech_forms.ops.cli db upgrade")

    if not actions:
        actions.append("No action required.")

    return _dedupe_keep_order(actions)


def _status_from_issues(issues: tuple[DriftIssue, ...]) -> str:
    if not issues:
        return "ok"
    if any(issue.severity == "error" for issue in issues):
        return "error"
    return "warn"


def _get_alembic_head(repo_root: Path) -> str:
    config = Config(str(repo_root / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    heads = tuple(sorted(script.get_heads()))
    if not heads:
        return ""
    if len(heads) == 1:
        return heads[0]
    return ",".join(heads)


def inspect_sqlite_db(
    db_path: str | Path,
    *,
    repo_root: Path | None = None,
) -> DoctorReport:
    effective_repo_root = repo_root or find_repo_root()
    db_path_resolved = resolve_repo_path(db_path, effective_repo_root)
    default_db_path = resolve_repo_path(DEFAULT_DB_RELATIVE_PATH, effective_repo_root)
    alembic_head = _get_alembic_head(effective_repo_root)

    db_exists = db_path_resolved.exists()
    sqlite_readable = False
    sqlite_corrupted = False
    error: str | None = None
    tables_present: tuple[str, ...] = ()
    alembic_check = AlembicCheck(table_exists=False, versions=(), version_matches_head=False)
    expected_check = ExpectedTablesCheck(
        missing_tables=EXPECTED_TABLES,
        missing_core_tables=CORE_TABLES,
        partial_schema=False,
        table_mismatches=(),
        schema_matches_head=False,
    )

    if db_exists and not db_path_resolved.is_file():
        error = "Database path exists but is not a file."
    elif db_exists:
        connection: sqlite3.Connection | None = None
        try:
            connection = open_db(db_path_resolved)
            quick_check_rows = connection.execute("PRAGMA quick_check").fetchall()
            quick_check_values = tuple(str(row[0]) for row in quick_check_rows if row and row[0] is not None)
            if not quick_check_values or any(value.lower() != "ok" for value in quick_check_values):
                sqlite_corrupted = True
                error = "; ".join(quick_check_values) if quick_check_values else "quick_check returned no rows"
            else:
                sqlite_readable = True
                tables_present = list_tables(connection)
                alembic_check = check_alembic_version(
                    connection,
                    table_names=tables_present,
                    alembic_head=alembic_head,
                )
                expected_check = check_expected_tables(connection, table_names=tables_present)
        except sqlite3.DatabaseError as exc:
            sqlite_corrupted = True
            error = str(exc)
        except sqlite3.Error as exc:
            error = str(exc)
        finally:
            if connection is not None:
                connection.close()

    issues = detect_drift_scenarios(
        db_exists=db_exists,
        sqlite_readable=sqlite_readable,
        sqlite_corrupted=sqlite_corrupted,
        error=error,
        alembic_version_table_exists=alembic_check.table_exists,
        alembic_versions=alembic_check.versions,
        missing_tables=expected_check.missing_tables,
        partial_schema=expected_check.partial_schema,
        table_mismatches=expected_check.table_mismatches,
        schema_matches_head=expected_check.schema_matches_head,
        version_matches_head=alembic_check.version_matches_head,
    )
    provisional_report = DoctorReport(
        db_path_input=str(db_path),
        db_path_resolved=str(db_path_resolved),
        default_db_path=str(default_db_path),
        db_exists=db_exists,
        sqlite_readable=sqlite_readable,
        sqlite_corrupted=sqlite_corrupted,
        error=error,
        alembic_head=alembic_head,
        alembic_version_table_exists=alembic_check.table_exists,
        alembic_versions=alembic_check.versions,
        tables_present=tables_present,
        expected_tables=EXPECTED_TABLES,
        missing_tables=expected_check.missing_tables,
        missing_core_tables=expected_check.missing_core_tables,
        partial_schema=expected_check.partial_schema,
        table_mismatches=expected_check.table_mismatches,
        schema_matches_head=expected_check.schema_matches_head,
        version_matches_head=alembic_check.version_matches_head,
        issues=issues,
        recommendations=(),
        status=_status_from_issues(issues),
    )
    recommendations = _build_recommendations(provisional_report)
    return DoctorReport(
        db_path_input=provisional_report.db_path_input,
        db_path_resolved=provisional_report.db_path_resolved,
        default_db_path=provisional_report.default_db_path,
        db_exists=provisional_report.db_exists,
        sqlite_readable=provisional_report.sqlite_readable,
        sqlite_corrupted=provisional_report.sqlite_corrupted,
        error=provisional_report.error,
        alembic_head=provisional_report.alembic_head,
        alembic_version_table_exists=provisional_report.alembic_version_table_exists,
        alembic_versions=provisional_report.alembic_versions,
        tables_present=provisional_report.tables_present,
        expected_tables=provisional_report.expected_tables,
        missing_tables=provisional_report.missing_tables,
        missing_core_tables=provisional_report.missing_core_tables,
        partial_schema=provisional_report.partial_schema,
        table_mismatches=provisional_report.table_mismatches,
        schema_matches_head=provisional_report.schema_matches_head,
        version_matches_head=provisional_report.version_matches_head,
        issues=provisional_report.issues,
        recommendations=recommendations,
        status=provisional_report.status,
    )


def render_doctor_report(report: DoctorReport) -> str:
    lines = [
        f"status: {report.status}",
        f"db_path_input: {report.db_path_input}",
        f"db_path_resolved: {report.db_path_resolved}",
        f"default_db_path: {report.default_db_path}",
        f"db_exists: {str(report.db_exists).lower()}",
        f"sqlite_readable: {str(report.sqlite_readable).lower()}",
        f"sqlite_corrupted: {str(report.sqlite_corrupted).lower()}",
        f"alembic_head: {report.alembic_head}",
        f"alembic_version_table_exists: {str(report.alembic_version_table_exists).lower()}",
        f"alembic_versions: {', '.join(report.alembic_versions) if report.alembic_versions else '<none>'}",
        f"tables_present: {', '.join(report.tables_present) if report.tables_present else '<none>'}",
        f"missing_tables: {', '.join(report.missing_tables) if report.missing_tables else '<none>'}",
        f"missing_core_tables: {', '.join(report.missing_core_tables) if report.missing_core_tables else '<none>'}",
        f"partial_schema: {str(report.partial_schema).lower()}",
        f"schema_matches_head: {str(report.schema_matches_head).lower()}",
        f"version_matches_head: {str(report.version_matches_head).lower()}",
    ]
    if report.error:
        lines.append(f"error: {report.error}")
    lines.append("issues:")
    if report.issues:
        for issue in report.issues:
            lines.append(f"- [{issue.severity}] {issue.code}: {issue.message}")
    else:
        lines.append("- none")
    if report.table_mismatches:
        lines.append("table_mismatches:")
        for mismatch in report.table_mismatches:
            lines.append(f"- {mismatch.table}: missing columns {', '.join(mismatch.missing_columns)}")
    lines.append("recommended_actions:")
    for index, action in enumerate(report.recommendations, start=1):
        lines.append(f"{index}. {action}")
    return "\n".join(lines)
