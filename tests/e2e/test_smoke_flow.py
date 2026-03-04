from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_smoke_create_publish_submit_export(client, runtime_env):
    headers = {"X-Admin-Token": runtime_env["admin_token"]}

    created = await client.post("/api/admin/forms", json={"title": "Smoke Flow"}, headers=headers)
    assert created.status_code == 201
    form = created.json()
    form_id = form["id"]
    slug = form["slug"]

    fields = await client.put(
        f"/api/admin/forms/{form_id}/fields",
        headers=headers,
        json={
            "fields": [
                {"key": "name", "label": "Name", "type": "text", "required": True, "options": []},
                {"key": "email", "label": "Email", "type": "email", "required": True, "options": []},
            ]
        },
    )
    assert fields.status_code == 200

    published = await client.post(f"/api/admin/forms/{form_id}/publish", headers=headers)
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    submitted = await client.post(
        f"/api/f/{slug}/submit",
        json={"values": {"name": "Smoke User", "email": "smoke@example.com"}},
    )
    assert submitted.status_code == 201

    exported = await client.get(f"/api/admin/forms/{form_id}/export.csv", headers=headers)
    assert exported.status_code == 200
    lines = exported.text.strip().splitlines()
    assert lines[0] == "submission_id,created_at,name,email"
    assert len(lines) == 2
