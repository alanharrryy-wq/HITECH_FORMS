from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def query_token(request: Request) -> str:
    return str(request.query_params.get("token", "")).strip()


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=303)
