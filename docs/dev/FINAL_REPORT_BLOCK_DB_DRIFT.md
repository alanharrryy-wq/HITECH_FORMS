# FINAL REPORT: BLOCK_DB_DRIFT

## 1) Summary
- Added a dedicated DB drift inspector module for SQLite (`src/hitech_forms/ops/db/doctor.py`) with deterministic structured output.
- Added safe recovery tooling (`backup`, `reset`, `stamp-head`) in `src/hitech_forms/ops/db/recovery.py`.
- Added new DB CLI commands:
  - `db doctor`
  - `db backup`
  - `db reset --yes-i-know`
  - `db stamp-head`
- DB CLI path handling now resolves `HFORMS_DB_PATH` directly; DB commands no longer require admin-token settings validation just to diagnose/recover schema drift.
- Hardened `db upgrade` failure handling to show actionable guidance (including `db doctor`) instead of raw stack traces.
- Added deterministic unit/integration tests for drift detection and upgrade error messaging.
- Added developer playbook: `docs/dev/DB_DRIFT_PLAYBOOK.md`.

## 2) New Commands & Flags
- `python -m hitech_forms.ops.cli db doctor`
  - `--json`: canonical JSON output.
- `python -m hitech_forms.ops.cli db backup`
  - default deterministic names: `backup_001.db`, `backup_002.db`, ...
  - `--with-timestamp`: optional timestamp suffix.
- `python -m hitech_forms.ops.cli db reset --yes-i-know`
  - guard rails:
    - allowed only when `HFORMS_ENV=dev` OR `HFORMS_ALLOW_DB_RESET=1`
    - requires explicit `--yes-i-know`
    - restricted to default DB path unless explicit override env is set.
  - emits run artifacts under `var/db_reset_runs/run-XXXX/`.
- `python -m hitech_forms.ops.cli db stamp-head`
  - strict mode:
    - only stamps when schema matches Alembic head checks.
    - refuses otherwise and points to doctor/recovery.

## 3) How To Reproduce Old Failure
1. Use drifted default DB (`var/hitech_forms.db`) where `submissions` table is missing.
2. Run:
   - `python -m hitech_forms.ops.cli db upgrade`
3. Current behavior (improved):
   - clean error summary, including:
     - `sqlite3.OperationalError: no such table: submissions`
     - `Run: python -m hitech_forms.ops.cli db doctor`
     - recommended next steps (`db backup`, `db reset --yes-i-know` in dev).

## 4) How To Recover Safely
1. Diagnose:
   - `python -m hitech_forms.ops.cli db doctor`
2. Backup:
   - `python -m hitech_forms.ops.cli db backup`
3. If doctor says schema==head but version drift exists:
   - `python -m hitech_forms.ops.cli db stamp-head`
4. If partial schema/missing core tables:
   - `HFORMS_ENV=dev python -m hitech_forms.ops.cli db reset --yes-i-know`
5. Verify:
   - `python -m hitech_forms.ops.cli db doctor`

## 5) Tests + Results
Executed from `F:\repos\HITECH_FORMS` using `.venv\Scripts\python.exe` with `PYTHONHASHSEED=0`:

- `python -m hitech_forms.ops.cli db doctor`
  - Pass (diagnoses legacy drift and recommends backup/reset).
- `python -m hitech_forms.ops.cli db upgrade` (default path)
  - Expected fail on existing drifted DB.
  - Pass criteria met: emits helpful guidance and `db doctor` pointer, no raw traceback.
- `python -m hitech_forms.ops.cli quality-check`
  - Pass.
- `pytest -q`
  - Pass (`39 passed`).
- `pytest -q tests/e2e -k smoke`
  - Pass (`2 passed`).

New test coverage added:
- `tests/unit/test_db_doctor.py`
- `tests/unit/test_db_recovery.py`
- `tests/unit/test_db_upgrade_error_message.py`
- `tests/integration/test_db_drift_doctor.py`

## 6) Files Changed List
Created:
- `docs/dev/DB_DRIFT_BLOCK_PLAN.md`
- `docs/dev/DB_DRIFT_PLAYBOOK.md`
- `docs/dev/FINAL_REPORT_BLOCK_DB_DRIFT.md`
- `src/hitech_forms/ops/db/__init__.py`
- `src/hitech_forms/ops/db/alembic.py`
- `src/hitech_forms/ops/db/doctor.py`
- `src/hitech_forms/ops/db/paths.py`
- `src/hitech_forms/ops/db/recovery.py`
- `tests/integration/test_db_drift_doctor.py`
- `tests/unit/test_db_doctor.py`
- `tests/unit/test_db_recovery.py`
- `tests/unit/test_db_upgrade_error_message.py`
- `tools/codex/BUNDLES/BLOCK_DB_DRIFT/STATUS.json`
- `tools/codex/BUNDLES/BLOCK_DB_DRIFT/FILES_CHANGED.json`
- `tools/codex/BUNDLES/BLOCK_DB_DRIFT/DIFF.patch`

Modified:
- `src/hitech_forms/ops/cli.py`
