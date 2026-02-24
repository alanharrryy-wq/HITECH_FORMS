#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

LOG_ROOT="tools/codex/D_validation/railway_runtime/logs"
mkdir -p "$LOG_ROOT"

if [[ -n "${DATABASE_URL:-}" ]] && [[ -f "migrations/alembic.ini" ]] && command -v alembic >/dev/null 2>&1; then
  if ! alembic -c migrations/alembic.ini upgrade head >"$LOG_ROOT/alembic.stdout.log" 2>"$LOG_ROOT/alembic.stderr.log"; then
    printf '%s\n' "alembic migration failed; continuing startup (see $LOG_ROOT/alembic.stderr.log)" >&2
  fi
fi

exec env PYTHONPATH=src uvicorn hitech_forms.app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
