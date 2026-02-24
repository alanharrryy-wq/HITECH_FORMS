# API

All admin endpoints require `X-Admin-Token` (or `?token=` for SSR navigation).

## Health

- `GET /api/health`

## Admin Forms

- `GET /api/admin/forms?page=<int>&page_size=<int>`
- `POST /api/admin/forms`
  - body: `{ "title": "...", "slug": "optional" }`
- `GET /api/admin/forms/{form_id}`
- `PUT /api/admin/forms/{form_id}`
- `DELETE /api/admin/forms/{form_id}`
- `PUT /api/admin/forms/{form_id}/fields`
  - body: `{ "fields": [ { "key","label","type","required","options" } ] }`
- `POST /api/admin/forms/{form_id}/publish`

Allowed field types:
- `text`
- `textarea`
- `number`
- `email`
- `select`
- `checkbox`
- `date`

## Public Form

- `GET /api/f/{slug}`
- `POST /api/f/{slug}/submit`
  - body: `{ "values": { "<field_key>": "<value>" } }`

## Submissions

- `GET /api/admin/forms/{form_id}/submissions?page=<int>&page_size=<int>`
- `GET /api/admin/forms/{form_id}/submissions/{submission_id}`
- Submission payloads include `submission_seq` (monotonic sequence per form).

## Exports

- `GET /api/admin/forms/{form_id}/export.csv?version=v1`
- UTF-8 CSV, streaming response, deterministic header and row order.

## Error Format

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```
