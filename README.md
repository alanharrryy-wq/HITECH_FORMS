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
- `python -m hitech_forms.ops.cli webhooks run-once --limit 50`
- `python -m hitech_forms.ops.cli webhooks run-loop --interval 5 --limit 50`
- `python -m hitech_forms.ops.cli demo run --output-root var/demo_runs --submissions 10`

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

## Reliability Flags (Railway/Prod)

All new reliability features are disabled by default.

- `HFORMS_FEATURE_WEBHOOKS_OUTBOX=false`
- `HFORMS_FEATURE_RATE_LIMIT=false`
- `HFORMS_FEATURE_METRICS=false`
- `HFORMS_WEBHOOK_TARGET_URL=`
- `HFORMS_WEBHOOK_MAX_ATTEMPTS=8`
- `HFORMS_WEBHOOK_BASE_BACKOFF_SECONDS=5`
- `HFORMS_WEBHOOK_JITTER=0`
- `HFORMS_RATE_LIMIT_RPS_PUBLIC=0`
- `HFORMS_RATE_LIMIT_RPS_ADMIN=0`

Recommended Railway rollout:
1. Enable `HFORMS_FEATURE_WEBHOOKS_OUTBOX=true` and set `HFORMS_WEBHOOK_TARGET_URL`.
2. Run worker as a separate command process:
   - `python -m hitech_forms.ops.cli webhooks run-loop --interval 5 --limit 50`
3. Enable rate limiting with conservative values:
   - `HFORMS_FEATURE_RATE_LIMIT=true`
   - `HFORMS_RATE_LIMIT_RPS_PUBLIC=<value>`
   - `HFORMS_RATE_LIMIT_RPS_ADMIN=<value>`
4. Enable metrics only if needed:
   - `HFORMS_FEATURE_METRICS=true`

## Demo Evidence Run

Use deterministic demo tooling to produce investor artifacts:

- `python -m hitech_forms.ops.cli demo run --output-root var/demo_runs --submissions 10`
- Optional webhook processing during the run:
  - add `--run-webhooks true`
- Optional timestamp-based run folder:
  - add `--with-timestamp true`

Artifacts are written per run folder:
- `logs/events.jsonl`
- `exported.csv`
- `summary.json` (canonical)
- `env_snapshot.txt` (secrets redacted)

## Migration Strategy

- One linear Alembic history (`0001_initial` baseline).
- Replays verified in tests via upgrade/downgrade/upgrade cycle.
- SQLite-compatible deterministic schema creation.

See:
- `docs/KERNEL_CONTEXT.md`
- `docs/ARCHITECTURE.md`
- `docs/API.md`
- `docs/SECURITY.md`
