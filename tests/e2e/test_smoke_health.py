from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_smoke_health(client, runtime_env):
    health = await client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"ok": True, "service": "HITECH_FORMS"}

    token = runtime_env["admin_token"]
    admin = await client.get(f"/admin/forms?token={token}")
    assert admin.status_code == 200
