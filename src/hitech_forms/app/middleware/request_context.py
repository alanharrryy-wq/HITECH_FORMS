from __future__ import annotations

from fastapi import Request

from hitech_forms.platform.request_context import (
    bind_request_id,
    build_deterministic_request_id,
    reset_request_id,
    sanitize_request_id,
)

REQUEST_ID_HEADER = "X-Request-Id"


async def request_context_middleware(request: Request, call_next):
    incoming = sanitize_request_id(request.headers.get(REQUEST_ID_HEADER, ""))
    request_id = incoming or build_deterministic_request_id(request.method, request.url.path)
    token = bind_request_id(request_id)
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    finally:
        reset_request_id(token)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response
