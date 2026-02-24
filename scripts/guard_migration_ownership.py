from __future__ import annotations

import os
import subprocess
import sys

ALLOWED_AGENTS = {"B_tooling", "Z_aggregator"}
MIGRATIONS_PREFIX = "migrations/"


def _normalize(path: str) -> str:
    return path.replace("\\", "/").strip()


def _changed_files_from_git() -> list[str]:
    cmd = ["git", "diff", "--name-only", "HEAD"]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main(argv: list[str]) -> int:
    changed_files = argv[1:] or _changed_files_from_git()
    touched_migrations = [
        _normalize(path)
        for path in changed_files
        if _normalize(path).startswith(MIGRATIONS_PREFIX)
    ]
    if not touched_migrations:
        print("migration-ownership: ok (no migration changes)")
        return 0

    actor = os.getenv("HFORMS_AGENT", "").strip()
    if actor not in ALLOWED_AGENTS:
        print("migration-ownership: violation")
        print(f"  actor={actor or '<unset>'}")
        print("  allowed=B_tooling,Z_aggregator")
        for path in touched_migrations:
            print(f"  touched={path}")
        return 1

    print(f"migration-ownership: ok (actor={actor})")
    for path in touched_migrations:
        print(f"  touched={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
