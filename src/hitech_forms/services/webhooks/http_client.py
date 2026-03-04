from __future__ import annotations

from dataclasses import dataclass
from urllib import error, request


@dataclass(frozen=True)
class WebhookDeliveryResult:
    delivered: bool
    http_status: int | None
    response_snippet: str
    error_type: str | None
    error_message: str | None


def _normalize_snippet(raw: str) -> str:
    return " ".join(raw.replace("\r", " ").replace("\n", " ").split())[:300]


class WebhookHttpClient:
    def __init__(self, timeout_seconds: float = 5.0):
        self._timeout_seconds = timeout_seconds

    def deliver(self, *, target_url: str, payload_json: str, idempotency_key: str) -> WebhookDeliveryResult:
        body = payload_json.encode("utf-8")
        req = request.Request(
            url=target_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Idempotency-Key": idempotency_key,
            },
        )
        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as response:
                status = int(getattr(response, "status", 200))
                text = response.read().decode("utf-8", errors="replace")
                return WebhookDeliveryResult(
                    delivered=200 <= status < 300,
                    http_status=status,
                    response_snippet=_normalize_snippet(text),
                    error_type=None if 200 <= status < 300 else "http_status",
                    error_message=None if 200 <= status < 300 else f"http status {status}",
                )
        except error.HTTPError as exc:
            response_text = exc.read().decode("utf-8", errors="replace")
            return WebhookDeliveryResult(
                delivered=False,
                http_status=int(exc.code),
                response_snippet=_normalize_snippet(response_text),
                error_type="http_error",
                error_message=f"http error {exc.code}",
            )
        except error.URLError as exc:
            return WebhookDeliveryResult(
                delivered=False,
                http_status=None,
                response_snippet="",
                error_type="network_error",
                error_message=str(exc.reason),
            )
        except Exception as exc:  # pragma: no cover - defensive catch
            return WebhookDeliveryResult(
                delivered=False,
                http_status=None,
                response_snippet="",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
