from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


class AlembicCommandError(RuntimeError):
    def __init__(
        self,
        *,
        command: list[str],
        return_code: int,
        stdout: str,
        stderr: str,
    ) -> None:
        super().__init__(f"Alembic command failed with exit code {return_code}.")
        self.command = tuple(command)
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr


def run_alembic_command(
    *,
    repo_root: Path,
    db_path: Path,
    args: Sequence[str],
) -> subprocess.CompletedProcess[str]:
    alembic_ini = repo_root / "migrations" / "alembic.ini"
    cmd = [
        sys.executable,
        "-m",
        "alembic",
        "-c",
        str(alembic_ini),
        *args,
    ]
    env = os.environ.copy()
    env["HFORMS_DB_PATH"] = str(db_path)
    env.setdefault("HFORMS_ADMIN_TOKEN", "db-ops-token")
    env.setdefault("HFORMS_TIMEZONE", "UTC")
    env.setdefault("PYTHONHASHSEED", "0")
    process = subprocess.run(
        cmd,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise AlembicCommandError(
            command=cmd,
            return_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
        )
    return process
