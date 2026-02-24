from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from hitech_forms.api.router import api_router
from hitech_forms.app.lifespan import lifespan
from hitech_forms.app.responses import canonical_json_response
from hitech_forms.platform.errors import AppError
from hitech_forms.web.router import web_router

app = FastAPI(title="HITECH_FORMS", lifespan=lifespan)
app.include_router(api_router)
app.include_router(web_router)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    payload = {"error": {"code": exc.code, "message": exc.message}}
    return canonical_json_response(payload, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, _exc: RequestValidationError):
    payload = {"error": {"code": "validation_error", "message": "invalid request"}}
    return canonical_json_response(payload, status_code=422)
