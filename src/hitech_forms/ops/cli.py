from __future__ import annotations

import os
import subprocess
import sys

import typer

from hitech_forms.db import session_scope
from hitech_forms.db.repositories import FormRepository, SubmissionRepository
from hitech_forms.platform.determinism import ensure_determinism_env
from hitech_forms.platform.settings import get_settings
from hitech_forms.services import ExportService, FormService

app = typer.Typer(add_completion=False, help="HITECH_FORMS CLI")
db = typer.Typer(add_completion=False, help="Database commands")
app.add_typer(db, name="db")


def _run(cmd: list[str], env: dict[str, str] | None = None) -> None:
    subprocess.run(cmd, check=True, env=env)


@app.command()
def runserver(host: str | None = None, port: int | None = None) -> None:
    settings = get_settings()
    effective_host = host or settings.host
    effective_port = port or settings.port
    import uvicorn

    uvicorn.run("hitech_forms.app.main:app", host=effective_host, port=effective_port, reload=False)


@db.command("upgrade")
def db_upgrade() -> None:
    settings = get_settings()
    env = os.environ.copy()
    env["HFORMS_DB_PATH"] = settings.db_path
    _run(
        [sys.executable, "-m", "alembic", "-c", "migrations/alembic.ini", "upgrade", "head"],
        env=env,
    )


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


@app.command("quality-check")
def quality_check(with_coverage: bool = False) -> None:
    ensure_determinism_env()
    _run([sys.executable, "-m", "ruff", "check", "."])
    _run([sys.executable, "-m", "mypy", "src"])
    pytest_cmd = [sys.executable, "-m", "pytest", "-q"]
    if with_coverage:
        pytest_cmd.extend(["--cov=src/hitech_forms", "--cov-report=term-missing"])
    _run(pytest_cmd)


def main() -> None:
    get_settings()
    app()


if __name__ == "__main__":
    main()
