from __future__ import annotations

import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from sqlalchemy import select
from tests.helpers import create_published_form

from hitech_forms.db import session_scope
from hitech_forms.db.models import WebhookDeliveryLog, WebhookOutbox
from hitech_forms.db.repositories import WebhookOutboxRepository
from hitech_forms.ops.webhooks import webhooks_run_once
from hitech_forms.platform.settings import get_settings, reset_settings_cache
from hitech_forms.services.webhooks import WebhookOutboxService


class _WebhookServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, *, status_code: int, response_body: str):  # noqa: N803
        super().__init__(server_address, RequestHandlerClass)
        self.status_code = status_code
        self.response_body = response_body
        self.requests: list[dict[str, str]] = []


class _CaptureHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        self.server.requests.append(  # type: ignore[attr-defined]
            {
                "path": self.path,
                "body": body,
                "idempotency_key": self.headers.get("X-Idempotency-Key", ""),
            }
        )
        self.send_response(self.server.status_code)  # type: ignore[attr-defined]
        self.end_headers()
        self.wfile.write(self.server.response_body.encode("utf-8"))  # type: ignore[attr-defined]

    def log_message(self, format: str, *args):  # noqa: A003
        return


@contextmanager
def _webhook_server(*, status_code: int = 200, response_body: str = "ok"):
    server = _WebhookServer(("127.0.0.1", 0), _CaptureHandler, status_code=status_code, response_body=response_body)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}/hook", server.requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.anyio
async def test_enqueue_on_submission_and_worker_delivery(client, runtime_env, monkeypatch):
    with _webhook_server(status_code=200) as (url, requests):
        monkeypatch.setenv("HFORMS_FEATURE_WEBHOOKS_OUTBOX", "true")
        monkeypatch.setenv("HFORMS_WEBHOOK_TARGET_URL", url)
        reset_settings_cache()

        token = runtime_env["admin_token"]
        published = await create_published_form(client, token)
        response = await client.post(
            f"/api/f/{published['slug']}/submit",
            json={
                "values": {
                    "name": "Webhook User",
                    "email": "webhook@example.com",
                    "priority": "normal",
                    "notify": "true",
                }
            },
        )
        assert response.status_code == 201

        with session_scope() as session:
            outbox_rows = session.execute(select(WebhookOutbox)).scalars().all()
            assert len(outbox_rows) == 1
            assert outbox_rows[0].status == "PENDING"

        summary = webhooks_run_once(limit=10)
        assert summary == {"processed": 1, "delivered": 1, "retried": 0, "failed": 0}
        assert len(requests) == 1
        assert requests[0]["idempotency_key"]

        with session_scope() as session:
            outbox_row = session.execute(select(WebhookOutbox)).scalar_one()
            logs = session.execute(select(WebhookDeliveryLog)).scalars().all()
            assert outbox_row.status == "DELIVERED"
            assert outbox_row.attempt_count == 1
            assert outbox_row.delivered_at == 1700000000
            assert len(logs) == 1
            assert logs[0].attempt_no == 1
            assert logs[0].http_status == 200


@pytest.mark.anyio
async def test_idempotent_enqueue_no_duplicates(client, runtime_env, monkeypatch):
    with _webhook_server(status_code=202) as (url, _requests):
        monkeypatch.setenv("HFORMS_FEATURE_WEBHOOKS_OUTBOX", "true")
        monkeypatch.setenv("HFORMS_WEBHOOK_TARGET_URL", url)
        reset_settings_cache()

        token = runtime_env["admin_token"]
        published = await create_published_form(client, token)
        submission_payload = {
            "values": {
                "name": "Idempotent User",
                "email": "idem@example.com",
                "priority": "normal",
                "notify": "true",
            }
        }
        response = await client.post(f"/api/f/{published['slug']}/submit", json=submission_payload)
        assert response.status_code == 201
        created = response.json()

        with session_scope() as session:
            settings = get_settings()
            service = WebhookOutboxService(WebhookOutboxRepository(session), settings)
            duplicate = service.enqueue_submission(
                form_id=created["form_id"],
                form_version_id=created["form_version_id"],
                submission_id=created["id"],
                submission_seq=created["submission_seq"],
                created_at=created["created_at"],
                slug=published["slug"],
                answers=submission_payload["values"],
            )
            assert duplicate is not None
            assert duplicate.enqueued is False
            rows = session.execute(select(WebhookOutbox)).scalars().all()
            assert len(rows) == 1


@pytest.mark.anyio
async def test_worker_retries_then_fails_at_max_attempts(client, runtime_env, monkeypatch):
    with _webhook_server(status_code=500, response_body="fail") as (url, _requests):
        monkeypatch.setenv("HFORMS_FEATURE_WEBHOOKS_OUTBOX", "true")
        monkeypatch.setenv("HFORMS_WEBHOOK_TARGET_URL", url)
        monkeypatch.setenv("HFORMS_WEBHOOK_MAX_ATTEMPTS", "2")
        monkeypatch.setenv("HFORMS_WEBHOOK_BASE_BACKOFF_SECONDS", "5")
        monkeypatch.setenv("HFORMS_WEBHOOK_JITTER", "0")
        reset_settings_cache()

        token = runtime_env["admin_token"]
        published = await create_published_form(client, token)
        response = await client.post(
            f"/api/f/{published['slug']}/submit",
            json={
                "values": {
                    "name": "Retry User",
                    "email": "retry@example.com",
                    "priority": "high",
                    "notify": "false",
                }
            },
        )
        assert response.status_code == 201

        first = webhooks_run_once(limit=10)
        assert first == {"processed": 1, "delivered": 0, "retried": 1, "failed": 0}
        with session_scope() as session:
            outbox_row = session.execute(select(WebhookOutbox)).scalar_one()
            assert outbox_row.status == "PENDING"
            assert outbox_row.attempt_count == 1
            assert outbox_row.next_attempt_at == 1700000005

        monkeypatch.setenv("HFORMS_FIXED_NOW", "1700000005")
        second = webhooks_run_once(limit=10)
        assert second == {"processed": 1, "delivered": 0, "retried": 0, "failed": 1}
        with session_scope() as session:
            outbox_row = session.execute(select(WebhookOutbox)).scalar_one()
            assert outbox_row.status == "FAILED"
            assert outbox_row.attempt_count == 2


@pytest.mark.anyio
async def test_worker_claims_are_safe_under_concurrency(client, runtime_env, monkeypatch):
    with _webhook_server(status_code=200) as (url, requests):
        monkeypatch.setenv("HFORMS_FEATURE_WEBHOOKS_OUTBOX", "true")
        monkeypatch.setenv("HFORMS_WEBHOOK_TARGET_URL", url)
        reset_settings_cache()

        token = runtime_env["admin_token"]
        published = await create_published_form(client, token)
        for idx in range(5):
            response = await client.post(
                f"/api/f/{published['slug']}/submit",
                json={
                    "values": {
                        "name": f"Concurrent {idx}",
                        "email": f"worker{idx}@example.com",
                        "priority": "normal",
                        "notify": "true",
                    }
                },
            )
            assert response.status_code == 201

        summaries: list[dict[str, int]] = []

        def _run_worker() -> None:
            summaries.append(webhooks_run_once(limit=5))

        t1 = threading.Thread(target=_run_worker)
        t2 = threading.Thread(target=_run_worker)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        delivered_total = sum(item["delivered"] for item in summaries)
        processed_total = sum(item["processed"] for item in summaries)
        assert processed_total == 5
        assert delivered_total == 5
        assert len(requests) == 5
        assert len({item["idempotency_key"] for item in requests}) == 5
