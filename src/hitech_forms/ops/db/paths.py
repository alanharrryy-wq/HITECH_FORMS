from __future__ import annotations

from pathlib import Path

DEFAULT_DB_RELATIVE_PATH = Path("var/hitech_forms.db")


def _is_repo_root(path: Path) -> bool:
    return (path / "pyproject.toml").is_file() and (path / "src" / "hitech_forms").is_dir()


def find_repo_root(start: Path | None = None) -> Path:
    search_roots: list[Path] = []
    if start is not None:
        search_roots.append(start.resolve())
    search_roots.append(Path.cwd().resolve())
    search_roots.append(Path(__file__).resolve())

    visited: set[Path] = set()
    for root in search_roots:
        for candidate in [root, *root.parents]:
            if candidate in visited:
                continue
            visited.add(candidate)
            if _is_repo_root(candidate):
                return candidate
    raise RuntimeError("Unable to locate repository root (expected pyproject.toml + src/hitech_forms).")


def resolve_repo_path(path_value: str | Path, repo_root: Path) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()
