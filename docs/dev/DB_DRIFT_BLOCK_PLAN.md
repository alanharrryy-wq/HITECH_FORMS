# DB Drift Block Plan

## Scope
- Harden local DB tooling for legacy SQLite drift while keeping production safety and deterministic behavior.
- Keep migration source-of-truth in Alembic and avoid modifying existing migration files.

## Findings from Intake
- DB CLI entrypoint: `src/hitech_forms/ops/cli.py` (`db upgrade` currently shells out to Alembic).
- Default DB path: `var/hitech_forms.db` via `HFORMS_DB_PATH` in `src/hitech_forms/platform/settings.py`.
- Current `db upgrade` failure on legacy local DB emits raw subprocess exception behavior.

## Implementation Plan (Tasks 2-10)
1. Add dedicated DB inspector module (`src/hitech_forms/ops/db/doctor.py`) with deterministic structured diagnosis.
2. Add `db doctor` CLI command with stable text output and canonical JSON output mode.
3. Add `db backup` CLI command with deterministic monotonic filenames under `var/backups/`.
4. Add `db reset --yes-i-know` CLI command (dev-only guard + explicit override env) with evidence logs.
5. Add strict `db stamp-head` CLI command that only stamps when schema can be proven to match head.
6. Improve `db upgrade` errors to point developers to `db doctor` with actionable recovery steps.
7. Add deterministic unit tests for drift detection scenarios.
8. Add integration tests for partial-schema (`submissions` missing) diagnosis and recommendations.
9. Write `docs/dev/DB_DRIFT_PLAYBOOK.md` with symptoms, root cause, and safe recovery workflow.
10. Run validation gates and publish final report + bundle artifacts for this block.
