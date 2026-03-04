from __future__ import annotations

import pytest
from tests.helpers import create_published_form

from hitech_forms.app.dependencies import reset_rate_limiter_cache
from hitech_forms.platform.settings import reset_settings_cache


@pytest.mark.anyio
async def test_public_submission_rate_limit_flag(client, runtime_env, monkeypatch):
    monkeypatch.setenv("HFORMS_FEATURE_RATE_LIMIT", "true")
    monkeypatch.setenv("HFORMS_RATE_LIMIT_RPS_PUBLIC", "1")
    monkeypatch.setenv("HFORMS_RATE_LIMIT_RPS_ADMIN", "0")
    reset_settings_cache()
    reset_rate_limiter_cache()

    published = await create_published_form(client, runtime_env["admin_token"])
    first = await client.post(
        f"/api/f/{published['slug']}/submit",
        json={
            "values": {
                "name": "Rate User 1",
                "email": "rate1@example.com",
                "priority": "normal",
                "notify": "true",
            }
        },
    )
    second = await client.post(
        f"/api/f/{published['slug']}/submit",
        json={
            "values": {
                "name": "Rate User 2",
                "email": "rate2@example.com",
                "priority": "normal",
                "notify": "false",
            }
        },
    )
    assert first.status_code == 201
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"
    assert second.json()["error"]["details"]["scope"] == "public_submission"
    assert second.json()["error"]["details"]["limit_rps"] == 1


@pytest.mark.anyio
async def test_admin_rate_limit_flag(client, runtime_env, monkeypatch):
    monkeypatch.setenv("HFORMS_FEATURE_RATE_LIMIT", "true")
    monkeypatch.setenv("HFORMS_RATE_LIMIT_RPS_ADMIN", "1")
    monkeypatch.setenv("HFORMS_RATE_LIMIT_RPS_PUBLIC", "0")
    reset_settings_cache()
    reset_rate_limiter_cache()

    headers = {"X-Admin-Token": runtime_env["admin_token"]}
    first = await client.get("/api/admin/forms", headers=headers)
    second = await client.get("/api/admin/forms", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"
    assert second.json()["error"]["details"]["scope"] == "admin"
    assert second.json()["error"]["details"]["limit_rps"] == 1
