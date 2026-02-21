from __future__ import annotations

import subprocess
import sys

import typer

from hitech_forms.platform.determinism import ensure_determinism_env

app = typer.Typer(add_completion=False)


@app.command()
def lint():
    subprocess.run([sys.executable, "-m", "ruff", "check", "src", "tests"], check=True)
    subprocess.run([sys.executable, "-m", "ruff", "format", "--check", "src", "tests"], check=True)


@app.command()
def typecheck():
    subprocess.run([sys.executable, "-m", "mypy", "src"], check=True)


@app.command()
def start_smoke():
    # Reuse E2E smoke deterministically (no flaky UI automation)
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/e2e", "-k", "smoke_health"], check=True
    )


@app.command()
def e2e(flows: str = "smoke_health"):
    subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/e2e", "-k", flows], check=True)


@app.command()
def determinism_check():
    ensure_determinism_env()


def main():
    app()


if __name__ == "__main__":
    main()
