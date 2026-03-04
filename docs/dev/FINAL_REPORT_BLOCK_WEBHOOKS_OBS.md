# FINAL REPORT: BLOCK_WEBHOOKS_OBS

## 1) Summary of what was built
- Added industrial webhook outbox subsystem (schema, repo, service, worker, delivery logs, retries/backoff, idempotency, structured event logs) behind `HFORMS_FEATURE_WEBHOOKS_OUTBOX` (default OFF).
- Added deterministic, flag-gated in-memory rate limiting for admin and public submission endpoints using RPS controls.
- Added observability upgrades: correlation IDs, structured logs with request context/startup seed, split health endpoints (`/api/health`, `/api/health/db`), and minimal feature-gated metrics endpoint (`/api/metrics`).
- Added deterministic demo tooling (`demo run`) that executes create->publish->submit->export and writes evidence artifacts in run folders.
- Added extensive deterministic tests for webhook payload/hash, retry scheduling, idempotency, worker lifecycle (success/retry/fail), concurrency safety, rate limits, observability, migrations, and e2e smoke flow.

## 2) Feature flags added + default values
- `HFORMS_FEATURE_WEBHOOKS_OUTBOX=false`
- `HFORMS_FEATURE_RATE_LIMIT=false`
- `HFORMS_FEATURE_METRICS=false`
- `HFORMS_WEBHOOK_MAX_ATTEMPTS=8`
- `HFORMS_WEBHOOK_BASE_BACKOFF_SECONDS=5`
- `HFORMS_WEBHOOK_JITTER=0`
- `HFORMS_RATE_LIMIT_RPS_PUBLIC=0`
- `HFORMS_RATE_LIMIT_RPS_ADMIN=0`

Additional related config used by implementation:
- `HFORMS_WEBHOOK_TARGET_URL=` (empty = not configured/no enqueue)

## 3) DB schema changes + migration name
- New migration: `migrations/versions/0003_webhook_outbox.py`
- Added table `webhook_outbox`:
  - `id, created_at, next_attempt_at, attempt_count, status, target_url, payload_json, payload_sha256, idempotency_key, form_id, form_version_id, submission_id, last_error, delivered_at`
  - Unique idempotency key and polling indexes.
- Added table `webhook_delivery_log`:
  - `id, outbox_id, attempt_no, attempted_at, http_status, response_snippet, error_type, error_message`
  - FK to outbox, per-attempt uniqueness/indexes.

## 4) How to run
- DB upgrade:
  - `python -m hitech_forms.ops.cli db upgrade`
- Webhook worker:
  - Run once: `python -m hitech_forms.ops.cli webhooks run-once --limit 50`
  - Run loop: `python -m hitech_forms.ops.cli webhooks run-loop --interval 5 --limit 50`
- Demo evidence run:
  - `python -m hitech_forms.ops.cli demo run --output-root var/demo_runs --submissions 10`
  - Optional: `--run-webhooks true`
  - Optional timestamp folder: `--with-timestamp true`

## 5) Test results (commands + pass/fail)
Executed from repo root:
- `python -m hitech_forms.ops.cli db upgrade`
  - Fail on pre-existing default DB (`var/hitech_forms.db`) due prior inconsistent state (`no such table: submissions`).
- `HFORMS_DB_PATH=var/validate_upgrade_20260224.db python -m hitech_forms.ops.cli db upgrade`
  - Pass (fresh DB, upgraded through `0003_webhook_outbox`).
- `python -m hitech_forms.ops.cli quality-check`
  - Pass.
- `pytest -q`
  - Pass (`31 passed`).
- `pytest -q tests/e2e -k smoke`
  - Pass (`2 passed`).
- Additional CI wave checks:
  - `python -m hitech_forms.ops.ci determinism-check` Pass
  - `python -m hitech_forms.ops.ci lint` Pass
  - `python -m hitech_forms.ops.ci typecheck` Pass
  - `python -m hitech_forms.ops.ci start-smoke` Pass
  - `python -m hitech_forms.ops.ci e2e --flows smoke` Pass

## 6) Files created/modified (explicit list)
Modified:
- `.env.example`
- `README.md`
- `docs/API.md`
- `docs/KERNEL_CONTEXT.md`
- `src/hitech_forms/api/router.py`
- `src/hitech_forms/api/routers/__init__.py`
- `src/hitech_forms/api/routers/health.py`
- `src/hitech_forms/api/routers/public_forms.py`
- `src/hitech_forms/app/dependencies.py`
- `src/hitech_forms/app/lifespan.py`
- `src/hitech_forms/app/main.py`
- `src/hitech_forms/app/security/rate_limit.py`
- `src/hitech_forms/db/models/__init__.py`
- `src/hitech_forms/db/repositories/__init__.py`
- `src/hitech_forms/db/repositories/submission_repository.py`
- `src/hitech_forms/ops/cli.py`
- `src/hitech_forms/platform/__init__.py`
- `src/hitech_forms/platform/feature_flags.py`
- `src/hitech_forms/platform/logging.py`
- `src/hitech_forms/platform/settings.py`
- `src/hitech_forms/services/__init__.py`
- `src/hitech_forms/services/submission_service.py`
- `src/hitech_forms/web/routers/public_forms.py`
- `tests/conftest.py`
- `tests/e2e/test_smoke_health.py`
- `tests/integration/test_form_lifecycle.py`
- `tests/integration/test_migrations.py`
- `tests/integration/test_submission_invariants.py`

Created:
- `docs/dev/BLOCK_WEBHOOKS_OBS_PLAN.md`
- `migrations/versions/0003_webhook_outbox.py`
- `src/hitech_forms/api/routers/metrics.py`
- `src/hitech_forms/app/middleware/__init__.py`
- `src/hitech_forms/app/middleware/request_context.py`
- `src/hitech_forms/db/models/webhook_delivery_log.py`
- `src/hitech_forms/db/models/webhook_outbox.py`
- `src/hitech_forms/db/repositories/webhook_outbox_repository.py`
- `src/hitech_forms/ops/demo.py`
- `src/hitech_forms/ops/webhooks.py`
- `src/hitech_forms/platform/metrics.py`
- `src/hitech_forms/platform/request_context.py`
- `src/hitech_forms/services/webhooks/__init__.py`
- `src/hitech_forms/services/webhooks/http_client.py`
- `src/hitech_forms/services/webhooks/outbox_service.py`
- `src/hitech_forms/services/webhooks/payloads.py`
- `src/hitech_forms/services/webhooks/scheduler.py`
- `src/hitech_forms/services/webhooks/worker.py`
- `tests/e2e/test_smoke_flow.py`
- `tests/integration/test_demo_tooling.py`
- `tests/integration/test_observability.py`
- `tests/integration/test_rate_limit_flags.py`
- `tests/integration/test_webhook_outbox.py`
- `tests/unit/test_webhooks_determinism.py`

## 7) Notes on determinism + remaining tech debt
- Determinism maintained:
  - canonical JSON for payloads/responses/summary artifacts
  - deterministic idempotency key/hash
  - deterministic retry schedule; jitter disabled by default and deterministic when enabled
  - deterministic request ID generation when header absent (seed + counter + method/path hash)
  - tests rely on `PYTHONHASHSEED=0`, UTC, and fixed epoch fixtures.
- Remaining technical debt / follow-up:
  - In-memory rate limiting is per-process (expected for current scope).
  - Worker is in-process CLI (intentionally simple); production should run it as dedicated process.
  - Existing default local DB file may be left in partial migrated state by prior runs; fresh DB upgrade is clean.
