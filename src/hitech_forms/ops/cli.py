from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import typer

from hitech_forms.db import session_scope
from hitech_forms.db.repositories import FormRepository, SubmissionRepository
from hitech_forms.ops.db import (
    create_backup,
    find_repo_root,
    format_upgrade_failure,
    inspect_sqlite_db,
    render_doctor_report,
    reset_sqlite_db,
    resolve_repo_path,
    stamp_head_strict,
    summarize_report,
    upgrade_to_head,
)
from hitech_forms.ops.db.alembic import AlembicCommandError
from hitech_forms.ops.demo import run_demo_evidence
from hitech_forms.ops.webhooks import webhooks_run_loop, webhooks_run_once
from hitech_forms.platform.determinism import canonical_json_dumps, ensure_determinism_env
from hitech_forms.platform.settings import get_settings
from hitech_forms.services import ExportService, FormService

app = typer.Typer(add_completion=False, help="HITECH_FORMS CLI")
db = typer.Typer(add_completion=False, help="Database commands")
webhooks = typer.Typer(add_completion=False, help="Webhook worker commands")
demo = typer.Typer(add_completion=False, help="Deterministic demo tooling")
app.add_typer(db, name="db")
app.add_typer(webhooks, name="webhooks")
app.add_typer(demo, name="demo")


def _run(cmd: list[str], env: dict[str, str] | None = None, cwd: Path | None = None) -> None:
    subprocess.run(cmd, check=True, env=env, cwd=cwd or find_repo_root())


def _raw_db_path_from_env() -> str:
    return os.getenv("HFORMS_DB_PATH", "var/hitech_forms.db").strip() or "var/hitech_forms.db"


def _resolved_db_path(repo_root: Path) -> Path:
    return resolve_repo_path(_raw_db_path_from_env(), repo_root)


def _echo_process_output(process: subprocess.CompletedProcess[str]) -> None:
    if process.stdout.strip():
        typer.echo(process.stdout.rstrip())
    if process.stderr.strip():
        typer.echo(process.stderr.rstrip(), err=True)


@app.command()
def runserver(host: str | None = None, port: int | None = None) -> None:
    settings = get_settings()
    effective_host = host or settings.host
    effective_port = port or settings.port
    import uvicorn

    uvicorn.run("hitech_forms.app.main:app", host=effective_host, port=effective_port, reload=False)


@db.command("upgrade")
def db_upgrade() -> None:
    repo_root = find_repo_root()
    db_path = _resolved_db_path(repo_root)
    try:
        upgrade_to_head(repo_root=repo_root, db_path=db_path)
    except AlembicCommandError as exc:
        typer.secho(format_upgrade_failure(error=exc, db_path=db_path), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"db upgrade: upgraded to head ({db_path})")


@db.command("doctor")
def db_doctor(as_json: bool = typer.Option(False, "--json", help="Output canonical JSON report.")) -> None:
    repo_root = find_repo_root()
    report = inspect_sqlite_db(_raw_db_path_from_env(), repo_root=repo_root)
    if as_json:
        typer.echo(canonical_json_dumps(report.to_dict()))
        return
    typer.echo(render_doctor_report(report))


@db.command("backup")
def db_backup(
    with_timestamp: bool = typer.Option(
        False,
        "--with-timestamp",
        help="Append UTC epoch timestamp to backup filename (off by default).",
    ),
) -> None:
    repo_root = find_repo_root()
    db_path = _resolved_db_path(repo_root)
    backup_dir = resolve_repo_path("var/backups", repo_root)
    try:
        result = create_backup(db_path=db_path, backup_dir=backup_dir, with_timestamp=with_timestamp)
    except RuntimeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        canonical_json_dumps(
            {
                "source_db_path": result.source_db_path,
                "backup_path": result.backup_path,
                "with_timestamp": with_timestamp,
            }
        )
    )


@db.command("reset")
def db_reset(
    yes_i_know: bool = typer.Option(
        False,
        "--yes-i-know",
        help="Required confirmation to allow local DB reset.",
    ),
) -> None:
    repo_root = find_repo_root()
    db_path = _resolved_db_path(repo_root)
    try:
        result = reset_sqlite_db(repo_root=repo_root, db_path=db_path, yes_i_know=yes_i_know)
    except AlembicCommandError as exc:
        typer.secho(format_upgrade_failure(error=exc, db_path=db_path), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except RuntimeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        canonical_json_dumps(
            {
                "db_path": result.db_path,
                "default_db_path": result.default_db_path,
                "run_dir": result.run_dir,
                "removed_existing_db": result.removed_existing_db,
                "before_status": result.before_status,
                "after_status": result.after_status,
            }
        )
    )


@db.command("stamp-head")
def db_stamp_head() -> None:
    repo_root = find_repo_root()
    db_path = _resolved_db_path(repo_root)
    try:
        result = stamp_head_strict(repo_root=repo_root, db_path=db_path)
    except AlembicCommandError as exc:
        typer.secho(format_upgrade_failure(error=exc, db_path=db_path), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except RuntimeError as exc:
        typer.secho(
            f"{exc}\nRun: python -m hitech_forms.ops.cli db doctor",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1) from exc
    typer.echo(canonical_json_dumps({"db_path": result.db_path, **summarize_report(inspect_sqlite_db(db_path))}))
    if not result.stamped:
        typer.echo("db stamp-head: already at head; no changes made.")
    else:
        typer.echo("db stamp-head: stamped alembic_version to head.")


@app.command("seed-demo")
def seed_demo() -> None:
    with session_scope() as session:
        service = FormService(FormRepository(session))
        created = service.command_create_form(title="Demo Intake")
        service.command_replace_fields(
            form_id=created["id"],
            fields=[
                {"key": "name", "label": "Name", "type": "text", "required": True, "options": []},
                {
                    "key": "email",
                    "label": "Email",
                    "type": "email",
                    "required": True,
                    "options": [],
                },
                {
                    "key": "priority",
                    "label": "Priority",
                    "type": "select",
                    "required": True,
                    "options": ["low", "normal", "high"],
                },
            ],
        )
        service.command_publish_form(created["id"])
    typer.echo("seed-demo: created and published demo form")


@app.command("export-csv")
def export_csv(form_id: int, output: str, version: str = "v1") -> None:
    with session_scope() as session:
        export_service = ExportService(FormRepository(session), SubmissionRepository(session))
        with open(output, "w", encoding="utf-8", newline="") as handle:
            for chunk in export_service.stream_form_csv(form_id=form_id, export_version=version):
                handle.write(chunk)
    typer.echo(f"export-csv: wrote {output}")


@webhooks.command("run-once")
def webhooks_run_once_cmd(limit: int = 50) -> None:
    summary = webhooks_run_once(limit=limit)
    typer.echo(canonical_json_dumps(summary))


@webhooks.command("run-loop")
def webhooks_run_loop_cmd(interval: int = 5, limit: int = 50) -> None:
    try:
        webhooks_run_loop(interval_seconds=interval, limit=limit)
    except KeyboardInterrupt:
        typer.echo("webhooks run-loop: stopped")


@demo.command("run")
def demo_run_cmd(
    output_root: str = "var/demo_runs",
    submissions: int = 5,
    run_id: str | None = None,
    with_timestamp: bool = False,
    run_webhooks: bool = False,
) -> None:
    summary = run_demo_evidence(
        output_root=output_root,
        submissions=submissions,
        run_id=run_id,
        with_timestamp=with_timestamp,
        run_webhooks=run_webhooks,
    )
    typer.echo(canonical_json_dumps(summary))


@app.command("quality-check")
def quality_check(with_coverage: bool = False) -> None:
    ensure_determinism_env()
    repo_root = find_repo_root()
    _run([sys.executable, "-m", "ruff", "check", "."], cwd=repo_root)
    _run([sys.executable, "-m", "mypy", "src"], cwd=repo_root)
    pytest_cmd = [sys.executable, "-m", "pytest", "-q"]
    if with_coverage:
        pytest_cmd.extend(["--cov=src/hitech_forms", "--cov-report=term-missing"])
    _run(pytest_cmd, cwd=repo_root)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
