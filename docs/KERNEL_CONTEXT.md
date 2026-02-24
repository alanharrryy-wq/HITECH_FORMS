# Kernel Context

## Purpose

HITECH_FORMS is an MVP kernel for deterministic form lifecycle management:
- admin creates/edits/deletes forms
- dynamic field schemas are configured and ordered deterministically
- forms are published to public URLs
- submissions are stored and reviewed
- exports are streamed as stable CSV

## Runtime Invariants

- `HFORMS_ADMIN_TOKEN` must be present at startup.
- `HFORMS_TIMEZONE` must be `UTC`.
- `PYTHONHASHSEED` must be `0`.
- optional deterministic time source: `HFORMS_FIXED_NOW`.

## Core Boundaries

- API/Web layers call service layer only.
- Services call repositories only.
- Repositories own ORM access and query ordering.
- ORM models are not returned by API/web.

## Deterministic Data Rules

- Stable slug normalization and collision suffixing.
- Stable ordering in list endpoints: `created_at`, then `id`.
- Stable field ordering: `position`, then `id`.
- Canonical JSON: sorted keys and compact separators.
- CSV export includes headers and deterministic column order.
