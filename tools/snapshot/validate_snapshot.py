import json
from pathlib import Path

def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    while True:
        if (current / ".git").exists() or (current / "pyproject.toml").exists():
            return current
        if current.parent == current:
            raise RuntimeError("Repo root not found (.git or pyproject.toml missing above).")
        current = current.parent

def fail(msg: str):
    print("Snapshot validation FAIL")
    print(msg)
    raise SystemExit(1)

def main():
    root = find_repo_root(Path(__file__).resolve())
    schema_path = root / "docs" / "snapshots" / "HITECH_FORMS__SNAPSHOT_MINI.schema.json"
    snap_path = root / "docs" / "snapshots" / "HITECH_FORMS__SNAPSHOT_MINI.json"

    if not schema_path.exists():
        fail(f"Missing schema: {schema_path}")
    if not snap_path.exists():
        fail(f"Missing snapshot: {snap_path}")

    # Lightweight validation: structural required keys + no extra top-level keys
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    snap = json.loads(snap_path.read_text(encoding="utf-8"))

    required = set(schema.get("required", []))
    missing = [k for k in sorted(required) if k not in snap]
    if missing:
        fail(f"Missing required top-level keys: {missing}")

    allowed = set(schema.get("properties", {}).keys())
    extra = [k for k in sorted(snap.keys()) if k not in allowed]
    if extra:
        fail(f"Extra top-level keys not allowed: {extra}")

    print("Snapshot validation PASS")

if __name__ == "__main__":
    main()
