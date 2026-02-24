# HITECH_FORMS

Deterministic industrial MVP for managed forms: create/edit/publish forms, collect submissions, and export streaming CSV.

## Quickstart

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r requirements-dev.txt`
3. Configure environment:
   - copy `.env.example` to `.env`
   - set `HFORMS_ADMIN_TOKEN`
   - set `PYTHONHASHSEED=0`
4. Run migrations:
   - `python -m hitech_forms.ops.cli db upgrade`
5. Start server:
   - `python -m hitech_forms.ops.cli runserver`

## Commands

- `python -m hitech_forms.ops.cli db upgrade`
- `python -m hitech_forms.ops.cli runserver`
- `python -m hitech_forms.ops.cli seed-demo`
- `python -m hitech_forms.ops.cli export-csv --form-id <id> --output <path>`
- `python -m hitech_forms.ops.cli quality-check`
- `python -m hitech_forms.ops.ci lint`
- `python -m hitech_forms.ops.ci typecheck`

## Dev Workflow

1. `ruff check .`
2. `mypy src`
3. `pytest -q`
4. `python -m alembic -c migrations/alembic.ini upgrade head`

## Folder Map

- `src/hitech_forms/app`: startup lifecycle, dependency wiring, response helpers
- `src/hitech_forms/api`: JSON API routes
- `src/hitech_forms/web`: SSR routes and templates
- `src/hitech_forms/services`: command/query service layer
- `src/hitech_forms/db`: SQLAlchemy engine/session/models/repositories
- `src/hitech_forms/platform`: determinism, settings, slugging, logging, errors
- `migrations`: Alembic migration environment and revisions
- `tests`: unit/integration/e2e deterministic suite
- `docs`: architecture, kernel context, API, security

## Determinism Notes

- UTC-only runtime (`HFORMS_TIMEZONE=UTC`).
- Hash seed enforced (`PYTHONHASHSEED=0`).
- Optional frozen time (`HFORMS_FIXED_NOW`).
- Stable query ordering on list and pagination endpoints.
- Canonical JSON serialization for API responses.
- Stable CSV header and row ordering.

## Migration Strategy

- One linear Alembic history (`0001_initial` baseline).
- Replays verified in tests via upgrade/downgrade/upgrade cycle.
- SQLite-compatible deterministic schema creation.

See:
- `docs/KERNEL_CONTEXT.md`
- `docs/ARCHITECTURE.md`
- `docs/API.md`
- `docs/SECURITY.md`
