import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    while True:
        if (current / ".git").exists() or (current / "pyproject.toml").exists():
            return current
        if current.parent == current:
            raise RuntimeError("Repo root not found (.git or pyproject.toml missing above).")
        current = current.parent


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def run_git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_tool_presence(pyproject_txt: str, requirements_txt: str, token: str) -> str:
    needle = token.lower()
    if needle in pyproject_txt.lower() or needle in requirements_txt.lower():
        return "PRESENT"
    return "UNKNOWN"


def main() -> None:
    root = find_repo_root(Path(__file__).resolve())
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    pyproject = root / "pyproject.toml"
    req = root / "requirements.txt"
    req_dev = root / "requirements-dev.txt"

    pyproject_txt = read_text(pyproject)
    requirements_txt = read_text(req) + "\n" + read_text(req_dev)

    tracked = [p for p in run_git(root, "ls-files").splitlines() if p.strip()]
    untracked = [p for p in run_git(root, "ls-files", "--others", "--exclude-standard").splitlines() if p.strip()]
    status_lines = [l for l in run_git(root, "status", "--short").splitlines() if l.strip()]

    tracked_files = []
    tracked_total_size = 0
    top_level_counts = {}
    extension_counts = {}

    for rel in tracked:
        rel_path = Path(rel)
        abs_path = root / rel_path
        if not abs_path.exists() or not abs_path.is_file():
            continue

        size = abs_path.stat().st_size
        digest = sha256_file(abs_path)
        tracked_total_size += size

        top = rel_path.parts[0] if rel_path.parts else "."
        top_level_counts[top] = top_level_counts.get(top, 0) + 1

        ext = rel_path.suffix.lower() if rel_path.suffix else "<no_ext>"
        extension_counts[ext] = extension_counts.get(ext, 0) + 1

        tracked_files.append(
            {
                "path": rel_path.as_posix(),
                "size_bytes": size,
                "sha256": digest,
            }
        )

    head_commit = run_git(root, "rev-parse", "HEAD")
    branch = run_git(root, "branch", "--show-current")
    origin_fetch = run_git(root, "remote", "get-url", "origin")
    remotes_raw = run_git(root, "remote", "-v")

    requirements_files = [p.name for p in [req, req_dev] if p.exists()]
    key_dirs = ["src", "tests", "tools", "migrations", "var", "docs", "scripts"]
    key_dir_state = {d: ("PRESENT" if (root / d).is_dir() else "MISSING") for d in key_dirs}

    snapshot = {
        "schema_version": "1.0.0",
        "generated_at_utc": now,
        "repo": {
            "root": str(root),
            "has_git": (root / ".git").exists(),
            "branch": branch,
            "head_commit": head_commit,
            "origin_url": origin_fetch if origin_fetch else None,
            "remotes_raw": remotes_raw.splitlines() if remotes_raw else [],
        },
        "runtime": {
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
        },
        "layout": {
            "top_level_dirs": sorted([p.name for p in root.iterdir() if p.is_dir() and p.name != ".git"]),
            "key_dirs": key_dir_state,
            "top_level_tracked_file_counts": dict(sorted(top_level_counts.items())),
            "tracked_extension_counts": dict(sorted(extension_counts.items())),
        },
        "tooling": {
            "pyproject_present": pyproject.exists(),
            "requirements_files": sorted(requirements_files),
            "pytest": parse_tool_presence(pyproject_txt, requirements_txt, "pytest"),
            "ruff": parse_tool_presence(pyproject_txt, requirements_txt, "ruff"),
            "mypy": parse_tool_presence(pyproject_txt, requirements_txt, "mypy"),
        },
        "git_status": {
            "is_clean": len(status_lines) == 0,
            "status_lines": status_lines,
            "tracked_files_count": len(tracked_files),
            "tracked_total_size_bytes": tracked_total_size,
            "untracked_non_ignored": sorted(untracked),
        },
        "files_tracked": tracked_files,
        "health_checks": {
            "preferred_test_command": "python -m pytest -q",
            "alternate_test_commands": ["pytest -q"],
        },
    }

    out = root / "docs" / "snapshots" / "HITECH_FORMS__SNAPSHOT_FULL.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Generated full snapshot at: {out}")


if __name__ == "__main__":
    main()
