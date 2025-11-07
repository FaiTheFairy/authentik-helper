# routers/pages.py
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from core.auth import require_user
from tools.settings import settings
from web.templates import templates

logger = logging.getLogger("authentik_helper.app")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request, user: dict = Depends(require_user)) -> HTMLResponse:
    ctx = {
        "request": request,
        "user": user,
        "base_url": settings.AK_BASE_URL,
        "invite_flow": settings.AK_INVITE_FLOW_SLUG,
        "invite_expires_days": settings.AK_INVITE_EXPIRES_DAYS,
        "portal_url": getattr(settings, "PORTAL_URL", None),
        "org_name": getattr(settings, "ORGANIZATION_NAME", None),
        "external_url": getattr(settings, "EXTERNAL_BASE_URL", None),
    }
    common = getattr(request.app.state, "common_ctx", lambda: {})()
    ctx.update(common)
    return templates.TemplateResponse(request, "index.html", ctx)
