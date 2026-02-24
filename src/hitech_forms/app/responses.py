from __future__ import annotations

from typing import Any

from fastapi import Response

from hitech_forms.platform.determinism import canonical_json_dumps


def canonical_json_response(payload: Any, status_code: int = 200) -> Response:
    return Response(
        content=canonical_json_dumps(payload),
        media_type="application/json; charset=utf-8",
        status_code=status_code,
    )
