from __future__ import annotations

import pytest
from tests.helpers import create_published_form


@pytest.mark.anyio
async def test_export_is_deterministic_across_calls(client, runtime_env):
    token = runtime_env["admin_token"]
    headers = {"X-Admin-Token": token}
    published = await create_published_form(client, token)
    slug = published["slug"]
    form_id = published["id"]

    for idx in range(3):
        response = await client.post(
            f"/api/f/{slug}/submit",
            json={
                "values": {
                    "name": f"User {idx}",
                    "email": f"user{idx}@example.com",
                    "priority": "normal",
                    "notify": "false",
                }
            },
        )
        assert response.status_code == 201

    first = await client.get(f"/api/admin/forms/{form_id}/export.csv", headers=headers)
    second = await client.get(f"/api/admin/forms/{form_id}/export.csv", headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.text == second.text


@pytest.mark.anyio
async def test_export_empty_form_is_header_only(client, runtime_env):
    token = runtime_env["admin_token"]
    headers = {"X-Admin-Token": token}
    published = await create_published_form(client, token)
    form_id = published["id"]

    export = await client.get(f"/api/admin/forms/{form_id}/export.csv", headers=headers)
    assert export.status_code == 200
    lines = export.text.strip().splitlines()
    assert lines == ["submission_id,created_at,name,email,priority,notify"]


@pytest.mark.anyio
async def test_export_large_dataset(client, runtime_env):
    token = runtime_env["admin_token"]
    headers = {"X-Admin-Token": token}
    published = await create_published_form(client, token)
    slug = published["slug"]
    form_id = published["id"]

    for idx in range(120):
        result = await client.post(
            f"/api/f/{slug}/submit",
            json={
                "values": {
                    "name": f"Load User {idx}",
                    "email": f"load{idx}@example.com",
                    "priority": "low" if idx % 2 == 0 else "high",
                    "notify": "true" if idx % 2 == 0 else "false",
                }
            },
        )
        assert result.status_code == 201

    export = await client.get(f"/api/admin/forms/{form_id}/export.csv", headers=headers)
    assert export.status_code == 200
    assert len(export.text.strip().splitlines()) == 121
