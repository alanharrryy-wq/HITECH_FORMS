from __future__ import annotations

import re

import pytest
from tests.helpers import create_published_form

from hitech_forms.platform.settings import reset_settings_cache


@pytest.mark.anyio
async def test_request_id_echo_and_generation(client):
    echoed = await client.get("/api/health", headers={"X-Request-Id": "demo-request-123"})
    generated = await client.get("/api/health")
    assert echoed.status_code == 200
    assert echoed.headers["X-Request-Id"] == "demo-request-123"
    assert generated.status_code == 200
    assert re.match(r"^[a-z0-9]{8,24}-\d{8}-[a-f0-9]{8}$", generated.headers["X-Request-Id"]) is not None


@pytest.mark.anyio
async def test_metrics_endpoint_flag_and_counters(client, runtime_env, monkeypatch):
    disabled = await client.get("/api/metrics")
    assert disabled.status_code == 404

    monkeypatch.setenv("HFORMS_FEATURE_METRICS", "true")
    reset_settings_cache()

    published = await create_published_form(client, runtime_env["admin_token"])
    response = await client.post(
        f"/api/f/{published['slug']}/submit",
        json={
            "values": {
                "name": "Metrics User",
                "email": "metrics@example.com",
                "priority": "low",
                "notify": "true",
            }
        },
    )
    assert response.status_code == 201

    metrics = await client.get("/api/metrics")
    assert metrics.status_code == 200
    lines = metrics.text.strip().splitlines()
    assert "submissions_total 1" in lines
    assert "webhook_outbox_pending 0" in lines
    assert "webhook_delivered_total 0" in lines
    assert "webhook_failed_total 0" in lines
