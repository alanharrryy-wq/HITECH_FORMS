import json
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    while True:
        if (current / ".git").exists() or (current / "pyproject.toml").exists():
            return current
        if current.parent == current:
            raise RuntimeError("Repo root not found (.git or pyproject.toml missing above).")
        current = current.parent

def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def exists_dir(p: Path) -> bool:
    return p.exists() and p.is_dir()

def exists_file(p: Path) -> bool:
    return p.exists() and p.is_file()

def main():
    script_path = Path(__file__).resolve()
    root = find_repo_root(script_path)

    notes_unknowns = []

    pyproject = root / "pyproject.toml"
    req = root / "requirements.txt"
    req_dev = root / "requirements-dev.txt"

    pyproject_present = exists_file(pyproject)
    if not pyproject_present:
        notes_unknowns.append("pyproject.toml missing; tooling detection may be partial.")

    req_files = []
    req_txt = ""

    for p in [req, req_dev]:
        if exists_file(p):
            req_files.append(p.name)
            req_txt += read_text(p)

    pyproject_txt = read_text(pyproject) if pyproject_present else ""

    def detect_tool(token: str) -> str:
        t = token.lower()
        if t in pyproject_txt.lower() or t in req_txt.lower():
            return "PRESENT"
        return "UNKNOWN"

    key_dirs = ["src","tests","tools","migrations","var"]
    key_dirs_state = {k: ("PRESENT" if exists_dir(root / k) else "MISSING") for k in key_dirs}

    caches = sorted([
        c for c in [".pytest_cache",".mypy_cache",".ruff_cache"]
        if exists_dir(root / c)
    ])

    snapshot = {
        "schema_version": "1.0.0",
        "repo": {
            "root": str(root),
            "has_git": exists_dir(root / ".git"),
            "python_version_hint": sys.version.split()[0],
            "venv_present": exists_dir(root / ".venv"),
            "pyproject_present": pyproject_present,
            "requirements_files": sorted(req_files),
        },
        "layout": {
            "dirs_present": sorted([d.name for d in root.iterdir() if d.is_dir() and d.name != ".git"]),
            "key_dirs": key_dirs_state,
            "caches_present": caches,
        },
        "python_tooling": {
            "pytest": detect_tool("pytest"),
            "ruff": detect_tool("ruff"),
            "mypy": detect_tool("mypy"),
        },
        "test_commands": {
            "preferred": "python -m pytest -q",
            "alternates": ["pytest -q"],
            "state": "PRESENT",
        },
        "health_checks": {
            "commands": ["python -m pytest -q"],
            "state": "PRESENT",
        },
        "notes_unknowns": sorted(notes_unknowns),
    }

    out = root / "docs" / "snapshots" / "HITECH_FORMS__SNAPSHOT_MINI.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Generated snapshot at: {out}")

if __name__ == "__main__":
    main()
