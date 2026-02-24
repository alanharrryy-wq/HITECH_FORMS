from __future__ import annotations

import asyncio

import pytest
from tests.helpers import create_published_form


@pytest.mark.anyio
async def test_submission_seq_is_unique_and_monotonic_per_form_under_concurrency(client, runtime_env):
    token = runtime_env["admin_token"]
    headers = {"X-Admin-Token": token}
    published = await create_published_form(client, token)
    slug = published["slug"]
    form_id = published["id"]
    submit_count = 20

    async def _submit(idx: int) -> dict:
        response = await client.post(
            f"/api/f/{slug}/submit",
            json={
                "values": {
                    "name": f"Concurrent {idx}",
                    "email": f"concurrent{idx}@example.com",
                    "priority": "normal",
                    "notify": "false",
                }
            },
        )
        assert response.status_code == 201
        return response.json()

    created = await asyncio.gather(*[_submit(idx) for idx in range(submit_count)])
    seqs = sorted(item["submission_seq"] for item in created)
    assert seqs == list(range(1, submit_count + 1))

    listed = await client.get(
        f"/api/admin/forms/{form_id}/submissions?page=1&page_size={submit_count}",
        headers=headers,
    )
    assert listed.status_code == 200
    list_payload = listed.json()
    assert [item["submission_seq"] for item in list_payload["items"]] == list(
        range(1, submit_count + 1)
    )


@pytest.mark.anyio
async def test_submission_seq_is_scoped_per_form(client, runtime_env):
    token = runtime_env["admin_token"]
    first = await create_published_form(client, token)
    second = await create_published_form(client, token)

    first_submission = await client.post(
        f"/api/f/{first['slug']}/submit",
        json={
            "values": {
                "name": "First Form User",
                "email": "first@example.com",
                "priority": "low",
                "notify": "false",
            }
        },
    )
    second_submission = await client.post(
        f"/api/f/{second['slug']}/submit",
        json={
            "values": {
                "name": "Second Form User",
                "email": "second@example.com",
                "priority": "high",
                "notify": "true",
            }
        },
    )
    assert first_submission.status_code == 201
    assert second_submission.status_code == 201
    assert first_submission.json()["submission_seq"] == 1
    assert second_submission.json()["submission_seq"] == 1


@pytest.mark.anyio
async def test_published_version_is_immutable(client, runtime_env):
    token = runtime_env["admin_token"]
    headers = {"X-Admin-Token": token}
    published = await create_published_form(client, token)
    form_id = published["id"]

    response = await client.put(
        f"/api/admin/forms/{form_id}/fields",
        headers=headers,
        json={
            "fields": [
                {"key": "name", "label": "Name", "type": "text", "required": True, "options": []},
                {"key": "updated", "label": "Updated", "type": "text", "required": False, "options": []},
            ]
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


@pytest.mark.anyio
async def test_submission_references_published_version_used_at_submit_time(client, runtime_env):
    token = runtime_env["admin_token"]
    headers = {"X-Admin-Token": token}
    published = await create_published_form(client, token)
    form_id = published["id"]
    detail = await client.get(f"/api/admin/forms/{form_id}", headers=headers)
    assert detail.status_code == 200
    active_version_id = detail.json()["active_version_id"]

    submitted = await client.post(
        f"/api/f/{published['slug']}/submit",
        json={
            "values": {
                "name": "Versioned User",
                "email": "versioned@example.com",
                "priority": "normal",
                "notify": "false",
            }
        },
    )
    assert submitted.status_code == 201
    payload = submitted.json()
    assert payload["form_id"] == form_id
    assert payload["form_version_id"] == active_version_id
