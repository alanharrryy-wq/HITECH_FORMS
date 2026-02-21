from __future__ import annotations

import json

from fastapi import APIRouter

from hitech_forms.platform.determinism import canonical_json_dumps

api_router = APIRouter(prefix="/api")


@api_router.get("/health")
def health():
    payload = {"ok": True, "service": "HITECH_FORMS"}
    return json.loads(canonical_json_dumps(payload))
