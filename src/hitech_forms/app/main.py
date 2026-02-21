from __future__ import annotations

from fastapi import FastAPI

from hitech_forms.api.router import api_router
from hitech_forms.app.lifespan import lifespan
from hitech_forms.web.router import web_router

app = FastAPI(title="HITECH_FORMS", lifespan=lifespan)
app.include_router(api_router)
app.include_router(web_router)
