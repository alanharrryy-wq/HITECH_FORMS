# Governance

## Ownership Policy

- `A_core` owns contracts, app composition, and global error/response policy.
- `B_tooling` owns `migrations/**`, CI/quality automation, and migration guards.
- `C_builder` owns form lifecycle API/service/repo modules.
- `D_submissions` owns submission and export API/service/repo modules.
- `E_web` owns SSR routers/templates/static assets.
- `Z_aggregator` owns orchestration docs and run artifacts under `tools/codex/Z_aggregator/**`.

## Migration Policy

- Migration files under `migrations/**` are B_tooling-only.
- Use `scripts/guard_migration_ownership.py` to enforce ownership in local/CI checks.
- Alembic reproducibility gate: `upgrade head`, `downgrade base`, `upgrade head`.

## Determinism Policy

- Keep `PYTHONHASHSEED=0` and `HFORMS_TIMEZONE=UTC`.
- Preserve ordering invariants from `hitech_forms.contracts.invariants`.
- No random/non-deterministic timestamps in tests (`HFORMS_FIXED_NOW` in fixtures).
