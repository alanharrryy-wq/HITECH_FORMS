from __future__ import annotations

import subprocess
import sys

import typer

from hitech_forms.platform.determinism import ensure_determinism_env

app = typer.Typer(add_completion=False)


@app.command()
def lint():
    subprocess.run([sys.executable, "-m", "ruff", "check", "."], check=True)


@app.command()
def typecheck():
    subprocess.run([sys.executable, "-m", "mypy", "src"], check=True)


@app.command()
def start_smoke():
    subprocess.run([sys.executable, "-m", "pytest", "-q", "tests", "-k", "smoke_health"], check=True)


@app.command()
def e2e(flows: str = "smoke_health"):
    subprocess.run([sys.executable, "-m", "pytest", "-q", "tests", "-k", flows], check=True)


@app.command()
def determinism_check():
    ensure_determinism_env()


def main():
    app()


if __name__ == "__main__":
    main()
