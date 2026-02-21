from __future__ import annotations

import httpx
import pytest


@pytest.mark.anyio
async def test_smoke_health():
    from hitech_forms.app.main import app as asgi_app

    transport = httpx.ASGITransport(app=asgi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"ok": True, "service": "HITECH_FORMS"}

        r2 = await client.get("/admin/forms")
        assert r2.status_code == 200
