# web/app_factory.py
from __future__ import annotations

import mimetypes
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version as pkg_version
from importlib.resources import files
from typing import Any, Dict
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import SecretStr

from core.middleware import get_request_id, request_log_middleware
from routers import invites, membership, pages, public, users
from services.brand import brand_ctx, refresh_brand_defaults
from tools.logging_config import setup_logging
from tools.settings import settings
from web.error_handlers import register as register_error_handlers
from services.build import build_ctx


def _trusted_hosts() -> list[str]:
    hosts: set[str] = {"localhost", "127.0.0.1"}
    try:
        ext = str(settings.EXTERNAL_BASE_URL or "")
        if ext:
            parts = urlsplit(ext)
            if parts.netloc:
                hosts.add(parts.netloc)
            if parts.hostname:
                hosts.add(parts.hostname)
    except Exception:
        pass
    return sorted(hosts)


def _app_version() -> str:
    try:
        return pkg_version("authentik-helper")
    except PackageNotFoundError:
        return "0+unknown"


def create_app(title: str = "Authentik Helper") -> FastAPI:
    # logging first so everything after logs consistently
    setup_logging(
        get_request_id=get_request_id,
        level=settings.LOG_LEVEL,
        file_path="./logs/app.ndjson",
        file_rotate="size",
        max_bytes=10 * 1024 * 1024,
        backup_count=7,
    )

    # lifespan replaces deprecated on_event("startup")
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.brand = refresh_brand_defaults()
        app.state.build = build_ctx(app)
        yield

    app = FastAPI(title=title, version=_app_version(), lifespan=lifespan)

    # middleware
    app.middleware("http")(request_log_middleware())
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_trusted_hosts())

    ext = str(settings.EXTERNAL_BASE_URL or "")
    https_only = ext.startswith("https://")
    if isinstance(settings.SESSION_SECRET, SecretStr):
        session_secret: str = settings.SESSION_SECRET.get_secret_value()
    else:
        session_secret: str = str(settings.SESSION_SECRET or "")

    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret,
        same_site="lax",
        https_only=https_only,
    )

    # common ctx
    def common_ctx() -> Dict[str, Any]:
        ctx: Dict[str, Any] = {}
        ctx.update(brand_ctx(app))
        ctx.update(getattr(app.state, "build", {}) or {})
        return ctx

    app.state.common_ctx = common_ctx

    # static + assets
    _STATIC_DIR = files("web").joinpath("static")
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    mimetypes.add_type("application/manifest+json", ".webmanifest")

    _SW_PATH = _STATIC_DIR / "js" / "sw.js"
    _MANIFEST_PATH = _STATIC_DIR / "manifest.webmanifest"

    @app.get("/sw.js", include_in_schema=False)
    def service_worker() -> FileResponse:
        headers = {"Cache-Control": "no-cache"}
        return FileResponse(str(_SW_PATH), media_type="application/javascript", headers=headers)

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest() -> FileResponse:
        return FileResponse(
            str(_MANIFEST_PATH),
            media_type="application/manifest+json; charset=utf-8",
        )

    # routers
    app.include_router(public.router)
    app.include_router(pages.router)
    app.include_router(users.router)
    app.include_router(membership.router)
    app.include_router(invites.router)

    # errors
    register_error_handlers(app)
    return app
