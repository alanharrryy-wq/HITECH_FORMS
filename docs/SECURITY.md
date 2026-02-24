# Security

## Admin Authentication

- Admin routes require token auth via `X-Admin-Token`.
- Startup fails fast if `HFORMS_ADMIN_TOKEN` is missing.
- Security-relevant auth failures are logged in structured form.

## Input Safety

- Slugs are sanitized and normalized before persistence.
- Duplicate slugs are rejected with explicit conflict errors.
- Field and submission values are validated by field type.

## Error Handling

- Domain/application exceptions are mapped centrally (`AppError`).
- API responses return compact error payloads; stack traces are not exposed.

## Rate Limiting Hook

- Minimal in-memory limiter is applied in admin guard.
- Limit is controlled by `HFORMS_RATE_LIMIT_PER_MINUTE`.

## CSRF Note

- SSR admin forms use token-based auth and are currently CSRF-exposed if token is shared in browser context.
- For production hardening, add CSRF tokens and same-site cookie strategy before internet-facing deployment.

## Recommended Hardening Next

- rotate admin token regularly
- put admin routes behind reverse-proxy auth/IP restrictions
- enforce HTTPS-only deployment
- add audit sink for structured security logs
