from hitech_forms.web.routers.admin_forms import build_admin_forms_web_router
from hitech_forms.web.routers.admin_submissions import build_admin_submissions_web_router
from hitech_forms.web.routers.public_forms import build_public_forms_web_router

__all__ = [
    "build_admin_forms_web_router",
    "build_admin_submissions_web_router",
    "build_public_forms_web_router",
]
