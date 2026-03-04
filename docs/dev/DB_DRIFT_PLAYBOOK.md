# DB Drift Playbook (Dev SQLite)

## Problem Summary
Legacy local SQLite files can drift away from Alembic state (for example: `alembic_version` says one revision, but core tables are missing). A common failure was:

- `sqlite3.OperationalError: no such table: submissions`

This playbook provides deterministic and safe local recovery commands.

## Symptoms
- `python -m hitech_forms.ops.cli db upgrade` fails on `var/hitech_forms.db`.
- `alembic_version` exists but expected tables/columns are missing.
- Partial schema exists (some of `forms/form_versions/fields/...` present, others absent).
- SQLite file is corrupted/unreadable.

## New Commands
- DB commands resolve `HFORMS_DB_PATH` directly and are usable even if app-level admin token config is not set.
- Diagnose only (no destructive action):
  - `python -m hitech_forms.ops.cli db doctor`
  - JSON mode: `python -m hitech_forms.ops.cli db doctor --json`
- Deterministic backup:
  - `python -m hitech_forms.ops.cli db backup`
  - filenames: `backup_001.db`, `backup_002.db`, ...
  - optional timestamp suffix: `--with-timestamp`
- Strict Alembic stamp:
  - `python -m hitech_forms.ops.cli db stamp-head`
  - only allowed when schema can be proven to match head.
- Dev-only reset:
  - `python -m hitech_forms.ops.cli db reset --yes-i-know`
  - requires `HFORMS_ENV=dev` or `HFORMS_ALLOW_DB_RESET=1`
  - default path protection: reset targets `var/hitech_forms.db` unless explicit override env is set.

## Safe Recovery Workflow
1. Run diagnosis:
   - `python -m hitech_forms.ops.cli db doctor`
2. If drift/corruption is detected, backup first:
   - `python -m hitech_forms.ops.cli db backup`
3. If doctor says schema matches head but Alembic version is missing/mismatched:
   - `python -m hitech_forms.ops.cli db stamp-head`
4. If doctor reports partial schema or missing core tables:
   - `HFORMS_ENV=dev python -m hitech_forms.ops.cli db reset --yes-i-know`
5. Re-run doctor to confirm:
   - `python -m hitech_forms.ops.cli db doctor`

## Reproducing Legacy Failure (Reference)
1. Use a drifted local DB where `submissions` table is missing but migration chain expects it.
2. Run:
   - `python -m hitech_forms.ops.cli db upgrade`
3. Expected message now:
   - clean failure summary
   - points to `python -m hitech_forms.ops.cli db doctor`
   - recommends backup/reset actions

## Determinism and Safety Notes
- Keep `PYTHONHASHSEED=0`.
- Keep timezone UTC (`HFORMS_TIMEZONE=UTC`).
- No auto-delete behavior exists: reset requires explicit `--yes-i-know`.
- Alembic remains source of truth; existing migration files are not rewritten.

## What Not To Do
- Do not blindly `stamp head` unless doctor indicates schema/head match.
- Do not delete SQLite DB without backup when data must be preserved.
- Do not edit historical migrations to paper over local drift.
