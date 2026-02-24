from __future__ import annotations

import pytest
from tests.helpers import create_published_form


@pytest.mark.anyio
async def test_create_form_and_get_detail(client, runtime_env):
    token = runtime_env["admin_token"]
    headers = {"X-Admin-Token": token}
    created = await client.post("/api/admin/forms", json={"title": "Incident Intake"}, headers=headers)
    assert created.status_code == 201
    payload = created.json()
    assert payload["title"] == "Incident Intake"
    assert payload["slug"] == "incident-intake"
    assert payload["status"] == "draft"

    detail = await client.get(f"/api/admin/forms/{payload['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == payload["id"]


@pytest.mark.anyio
async def test_publish_and_public_fetch(client, runtime_env):
    token = runtime_env["admin_token"]
    published = await create_published_form(client, token)

    public = await client.get(f"/api/f/{published['slug']}")
    assert public.status_code == 200
    public_payload = public.json()
    assert public_payload["status"] == "published"
    assert [field["key"] for field in public_payload["fields"]] == [
        "name",
        "email",
        "priority",
        "notify",
    ]


@pytest.mark.anyio
async def test_submit_and_list_submissions(client, runtime_env):
    token = runtime_env["admin_token"]
    headers = {"X-Admin-Token": token}
    published = await create_published_form(client, token)
    slug = published["slug"]
    form_id = published["id"]

    submit_payload = {
        "values": {
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "priority": "high",
            "notify": "true",
        }
    }
    submitted = await client.post(f"/api/f/{slug}/submit", json=submit_payload)
    assert submitted.status_code == 201

    listed = await client.get(f"/api/admin/forms/{form_id}/submissions", headers=headers)
    assert listed.status_code == 200
    list_payload = listed.json()
    assert list_payload["total"] == 1
    sub_id = list_payload["items"][0]["id"]

    detail = await client.get(f"/api/admin/forms/{form_id}/submissions/{sub_id}", headers=headers)
    assert detail.status_code == 200
    answers = detail.json()["answers"]
    assert answers["name"] == "Ada Lovelace"
    assert answers["priority"] == "high"


@pytest.mark.anyio
async def test_export_csv_headers_and_order(client, runtime_env):
    token = runtime_env["admin_token"]
    headers = {"X-Admin-Token": token}
    published = await create_published_form(client, token)
    slug = published["slug"]
    form_id = published["id"]

    for name, email, priority in [
        ("Alice", "alice@example.com", "low"),
        ("Bob", "bob@example.com", "high"),
    ]:
        response = await client.post(
            f"/api/f/{slug}/submit",
            json={
                "values": {
                    "name": name,
                    "email": email,
                    "priority": priority,
                    "notify": "true",
                }
            },
        )
        assert response.status_code == 201

    export = await client.get(f"/api/admin/forms/{form_id}/export.csv", headers=headers)
    assert export.status_code == 200
    lines = export.text.strip().splitlines()
    assert lines[0] == "submission_id,created_at,name,email,priority,notify"
    assert lines[1] == "1,1700000000,Alice,alice@example.com,low,true"
    assert lines[2] == "2,1700000000,Bob,bob@example.com,high,true"


@pytest.mark.anyio
async def test_admin_auth_enforced(client):
    no_auth = await client.get("/api/admin/forms")
    assert no_auth.status_code == 401


@pytest.mark.anyio
async def test_pagination_is_stable(client, runtime_env):
    token = runtime_env["admin_token"]
    headers = {"X-Admin-Token": token}
    for idx in range(5):
        created = await client.post(
            "/api/admin/forms",
            json={"title": f"Form {idx}", "slug": f"form-{idx}"},
            headers=headers,
        )
        assert created.status_code == 201

    page1 = await client.get("/api/admin/forms?page=1&page_size=2", headers=headers)
    page2 = await client.get("/api/admin/forms?page=2&page_size=2", headers=headers)
    assert page1.status_code == 200
    assert page2.status_code == 200
    names1 = [row["title"] for row in page1.json()["items"]]
    names2 = [row["title"] for row in page2.json()["items"]]
    assert names1 == ["Form 0", "Form 1"]
    assert names2 == ["Form 2", "Form 3"]
    assert page1.json()["has_next"] is True


@pytest.mark.anyio
async def test_field_reorder_is_deterministic(client, runtime_env):
    token = runtime_env["admin_token"]
    headers = {"X-Admin-Token": token}
    created = await client.post("/api/admin/forms", json={"title": "Reorder"}, headers=headers)
    assert created.status_code == 201
    form_id = created.json()["id"]

    initial = {
        "fields": [
            {"key": "a", "label": "A", "type": "text", "required": False, "options": []},
            {"key": "b", "label": "B", "type": "text", "required": False, "options": []},
            {"key": "c", "label": "C", "type": "text", "required": False, "options": []},
        ]
    }
    first = await client.put(f"/api/admin/forms/{form_id}/fields", json=initial, headers=headers)
    assert first.status_code == 200
    assert [field["key"] for field in first.json()["fields"]] == ["a", "b", "c"]

    reordered = {
        "fields": [
            {"key": "c", "label": "C", "type": "text", "required": False, "options": []},
            {"key": "a", "label": "A", "type": "text", "required": False, "options": []},
            {"key": "b", "label": "B", "type": "text", "required": False, "options": []},
        ]
    }
    second = await client.put(f"/api/admin/forms/{form_id}/fields", json=reordered, headers=headers)
    assert second.status_code == 200
    assert [field["key"] for field in second.json()["fields"]] == ["c", "a", "b"]
