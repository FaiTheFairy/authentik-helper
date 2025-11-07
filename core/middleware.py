# core/middleware.py
from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Awaitable, Callable

from fastapi import Request

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("authentik_helper.app")

# paths and prefixes we don't want to spam logs with
QUIET_PATHS = {
    "/favicon.ico",
    "/manifest.webmanifest",
    "/apple-touch-icon.png",
    "/healthz",
    "/sw.js",
}
QUIET_PREFIXES = ("/static/",)


def get_request_id() -> str | None:
    """pull the current request id from context (or None)"""
    return request_id_ctx.get()


def _quiet_path(path: str) -> bool:
    """true when a path is in the quiet list/prefixes"""
    return path in QUIET_PATHS or any(path.startswith(p) for p in QUIET_PREFIXES)


def request_log_middleware() -> Callable[[Request, Callable[..., Awaitable]], Awaitable]:
    """
    factory that returns the actual middleware callable.
    keeps a request id in a ContextVar, logs duration + status, and sets X-Request-Id.
    """

    async def _mw(request: Request, call_next: Callable[..., Awaitable]):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        token = request_id_ctx.set(rid)
        start = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        except Exception:
            # include stack
            logger.exception(
                "unhandled error during request %s %s", request.method, request.url.path
            )
            raise
        finally:
            dur = int((time.perf_counter() - start) * 1000)
            status = getattr(response, "status_code", 500) if response else 500

            if not _quiet_path(request.url.path):
                if status >= 500:
                    level = logging.ERROR
                elif status >= 400:
                    level = logging.WARNING
                else:
                    level = logging.INFO
                logger.log(
                    level,
                    "request_handled",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status": status,
                        "duration_ms": dur,
                    },
                )

            # setting headers (best-effort)
            try:
                if response is not None:
                    response.headers["X-Request-Id"] = rid
            except Exception:
                pass
            request_id_ctx.reset(token)

    return _mw
