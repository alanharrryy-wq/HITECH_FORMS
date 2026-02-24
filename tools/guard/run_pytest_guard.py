import subprocess
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path | None:
    p = start.resolve()
    for _ in range(50):
        if (p / ".git").exists() or (p / "pyproject.toml").exists():
            return p
        if p.parent == p:
            return None
        p = p.parent
    return None

PROJECT_DIR = find_repo_root(Path(__file__).resolve())
if PROJECT_DIR is None:
    raise RuntimeError("Unable to locate repo root from script path.")

def die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)

def main() -> int:
    cwd = Path.cwd()
    git_root = find_repo_root(cwd)

    if git_root is None:
        die(f"ERROR: Not inside any git repo. CWD={cwd}")

    # Hard fence: must be inside the intended project (any subfolder)
    try:
        cwd.resolve().relative_to(PROJECT_DIR)
    except Exception:
        die(
            "ERROR: You are NOT inside the allowed project.\n"
            f"  Allowed: {PROJECT_DIR}\n"
            f"  Current: {cwd.resolve()}\n"
            "Tip: cd into the repo and try again."
        )

    # Build pytest command (python -m pytest preferred)
    extra = sys.argv[1:]
    cmd = [sys.executable, "-m", "pytest", "-q", *extra]

    print(f"[HITECH_FORMS] OK • Repo={PROJECT_DIR} • CWD={cwd.resolve()}")
    print(f"[HITECH_FORMS] RUN: {' '.join(cmd)}")

    # Run from PROJECT_DIR for stable discovery/imports
    p = subprocess.run(cmd, cwd=str(PROJECT_DIR))
    return p.returncode

if __name__ == "__main__":
    raise SystemExit(main())
