# Architecture

## Layers

1. `platform`
   - settings validation
   - determinism utilities (clock, canonical JSON)
   - slug generation
   - structured logging and app error types
2. `db`
   - engine/session lifecycle
   - SQLAlchemy models
   - repositories with ordered queries and transaction-safe behavior
3. `services`
   - command/query operations
   - input validation and field-type rules
   - publish lifecycle
   - submission validation
   - CSV streaming orchestration
4. `api` and `web`
   - API endpoints and SSR pages
   - admin token enforcement via dependency injection
   - centralized error mapping from `AppError`

## Dependency Injection

- request-scoped dependencies create repositories/services from DB session.
- admin guard enforces token + rate-limit hook.
- export service is injected independently from form/submission services.

## Database Design

Tables:
- `forms`
- `form_versions`
- `fields`
- `submissions`
- `answers`

Indexes:
- `forms.slug`, `forms.created_at`
- `form_versions.form_id`, `form_versions.created_at`
- `fields.form_version_id`, `fields.position`
- `submissions.form_id`, `submissions.created_at`
- `answers.submission_id`, `answers.field_key`

## Command/Query Split

- Commands: create/update/delete/publish/replace-fields/submit.
- Queries: list forms, form detail, public form detail, list submissions, submission detail, export stream.

## Migration Strategy

- single baseline migration (`0001_initial`) to establish deterministic schema.
- migrations are replay-tested in CI (`upgrade head`, `downgrade base`, `upgrade head`).
- schema reflection assertions verify table/index presence.
