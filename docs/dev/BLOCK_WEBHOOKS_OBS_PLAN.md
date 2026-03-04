# BLOCK_WEBHOOKS_OBS Plan

## Scope Alignment
- Keep boundaries: API/Web -> Services -> Repositories -> ORM.
- Keep deterministic behavior: `PYTHONHASHSEED=0`, UTC timestamps, canonical JSON, stable ordering.
- Add all new behavior behind feature flags defaulting to OFF.

## Planned Module Additions
- `src/hitech_forms/platform/settings.py`
  - Add env-backed flags and webhook/rate-limit tuning values.
- `src/hitech_forms/platform/metrics.py` (new)
  - Minimal in-process counters and text exposition.
- `src/hitech_forms/app/middleware/request_context.py` (new)
  - Correlation ID handling and request-scoped context.
- `src/hitech_forms/app/security/rate_limit.py`
  - Deterministic fixed-window RPS limiters for `public` and `admin` scopes.
- `src/hitech_forms/services/webhooks/` (new package)
  - `payloads.py`: canonical payload + hashing/idempotency key.
  - `scheduler.py`: deterministic retry/backoff (+ optional deterministic jitter).
  - `outbox_service.py`: enqueue + status transitions.
  - `worker.py`: run-once/run-loop delivery executor.
  - `http_client.py`: lightweight webhook POST transport.
- `src/hitech_forms/db/models/`
  - Add `webhook_outbox.py`, `webhook_delivery_log.py`.
- `src/hitech_forms/db/repositories/` (new)
  - `webhook_outbox_repository.py`: DB persistence, claim/lock, delivery logs.
- `src/hitech_forms/api/routers/`
  - Extend `health.py` for `/api/health` + `/api/health/db`.
  - Add `metrics.py` router (feature-flag gated).
- `src/hitech_forms/ops/cli.py`
  - Add `webhooks run-once`, `webhooks run-loop`.
  - Add deterministic demo/evidence commands.

## Flags and Config (defaults)
- `HFORMS_FEATURE_WEBHOOKS_OUTBOX=false`
- `HFORMS_FEATURE_RATE_LIMIT=false`
- `HFORMS_FEATURE_METRICS=false`
- `HFORMS_WEBHOOK_MAX_ATTEMPTS=8`
- `HFORMS_WEBHOOK_BASE_BACKOFF_SECONDS=5`
- `HFORMS_WEBHOOK_JITTER=0`
- `HFORMS_RATE_LIMIT_RPS_PUBLIC=0`
- `HFORMS_RATE_LIMIT_RPS_ADMIN=0`

## Migration Plan
- Add a new Alembic revision after `0002_submission_seq` to create:
  - `webhook_outbox`
  - `webhook_delivery_log`
- Include indexes for deterministic work pickup (`status`, `next_attempt_at`, `id`) and FK linkage.

## Test Plan
- Unit: canonical payload/hash, retry schedule, deterministic jitter, idempotent enqueue, rate-limit boundaries.
- Integration: enqueue on submit (flag ON), worker delivery lifecycle, migration reflection includes new tables.
- E2E smoke: create -> publish -> submit -> export, health endpoints, and optional metrics check when enabled.

## Ops/Gates
- Validate with:
  - `python -m hitech_forms.ops.cli db upgrade`
  - `python -m hitech_forms.ops.cli quality-check`
  - `pytest -q`
  - `pytest -q tests/e2e -k smoke`
- Produce required final report and bundle artifacts under `tools/codex/BUNDLES/BLOCK_WEBHOOKS_OBS/`.
