from __future__ import annotations

import os
import subprocess
import sys

import typer

from hitech_forms.platform.settings import get_settings

app = typer.Typer(add_completion=False)

db = typer.Typer(add_completion=False)
app.add_typer(db, name="db")


@app.command()
def runserver(host: str = "127.0.0.1", port: int = 8000):
    import uvicorn

    uvicorn.run("hitech_forms.app.main:app", host=host, port=port, reload=False)


@db.command("upgrade")
def db_upgrade():
    s = get_settings()
    env = os.environ.copy()
    env["HFORMS_DB_PATH"] = s.db_path
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "migrations/alembic.ini", "upgrade", "head"],
        check=True,
        env=env,
    )


@app.command()
def seed(demo: bool = True):
    typer.echo("seed: demo placeholder (Wave 1) ✅")


def main():
    app()


if __name__ == "__main__":
    main()
