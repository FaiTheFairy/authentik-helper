# routers/public.py
from __future__ import annotations

import logging
from typing import Any, Dict
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from tools.settings import settings
from core.security import get_oidc
from web.templates import templates

logger = logging.getLogger("authentik_helper.app")
router = APIRouter()


def _callback_url(request: Request) -> str:
    """build absolute callback url when external base is configured"""
    cb_path = request.url_for("auth_callback").path
    return (
        (str(settings.EXTERNAL_BASE_URL).rstrip("/") + cb_path)
        if settings.EXTERNAL_BASE_URL
        else str(request.url_for("auth_callback"))
    )


@router.get("/login", include_in_schema=False)
def login_page(request: Request) -> Response:
    ctx = request.app.state.common_ctx()
    ctx["request"] = request
    return templates.TemplateResponse(request, "login.html", ctx)


@router.get("/healthz", include_in_schema=False)
def healthz():
    """basic liveness endpoint used by deploys and tests"""
    return {"ok": True}


@router.get("/login/oidc")
async def login_oidc(request: Request):
    """start an oidc authorization code flow"""
    oidc = get_oidc()
    return await oidc.authorize_redirect(request, _callback_url(request))


@router.get("/auth/callback")
async def auth_callback(request: Request):
    """
    finish oidc login using the userinfo endpoint.
    stores a compact user dict in the session.
    """
    oidc = get_oidc()
    token = await oidc.authorize_access_token(request)

    try:
        uinfo = await oidc.userinfo(token=token)
    except Exception as e:
        logger.warning("userinfo_fetch_failed", extra={"error": str(e)})
        uinfo = {}

    claims: Dict[str, Any] = uinfo or {}
    request.session["user"] = {
        "sub": claims.get("sub"),
        "email": claims.get("email"),
        "name": claims.get("name") or claims.get("preferred_username"),
        "picture": claims.get("picture") or None,
    }
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    """clear session and try to hit the provider end_session endpoint"""
    request.session.pop("user", None)
    try:
        end_session = get_oidc().server_metadata.get("end_session_endpoint")
    except Exception:
        end_session = None

    post_logout = str(settings.EXTERNAL_BASE_URL) or "/"
    if end_session:
        qs = urlencode({"post_logout_redirect_uri": post_logout})
        return RedirectResponse(f"{end_session}?{qs}")
    return RedirectResponse("/", status_code=303)
