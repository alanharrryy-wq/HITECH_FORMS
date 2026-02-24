from __future__ import annotations

import httpx


async def create_published_form(client: httpx.AsyncClient, token: str) -> dict:
    headers = {"X-Admin-Token": token}
    created = await client.post("/api/admin/forms", json={"title": "Customer Intake"}, headers=headers)
    assert created.status_code == 201
    created_payload = created.json()
    form_id = created_payload["id"]
    field_payload = {
        "fields": [
            {"key": "name", "label": "Name", "type": "text", "required": True, "options": []},
            {"key": "email", "label": "Email", "type": "email", "required": True, "options": []},
            {
                "key": "priority",
                "label": "Priority",
                "type": "select",
                "required": True,
                "options": ["low", "normal", "high"],
            },
            {"key": "notify", "label": "Notify", "type": "checkbox", "required": False, "options": []},
        ]
    }
    replaced = await client.put(f"/api/admin/forms/{form_id}/fields", json=field_payload, headers=headers)
    assert replaced.status_code == 200
    published = await client.post(f"/api/admin/forms/{form_id}/publish", headers=headers)
    assert published.status_code == 200
    return published.json()
