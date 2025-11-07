# web/error_handlers.py
from __future__ import annotations

import logging
from typing import Any, Dict

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("authentik_helper.app")


def _problem(status: int, detail: str, extra: Dict[str, Any] | None = None) -> JSONResponse:
    # build a simple json error response
    body: Dict[str, Any] = {"detail": detail}
    if extra:
        body.update(extra)
    return JSONResponse(status_code=status, content=body)


def register(app: FastAPI) -> None:
    # handle runtime errors as internal server errors (500)
    @app.exception_handler(RuntimeError)
    async def _runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
        logger.error(
            "runtime_error",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(exc),
            },
        )
        return _problem(500, "backend unavailable")

    # handle transport errors from requests as bad gateway (502)
    @app.exception_handler(httpx.RequestError)
    async def _requests_error_handler(request: Request, exc: httpx.RequestError) -> JSONResponse:
        logger.error(
            "transport_error",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(exc),
            },
        )
        return _problem(502, "backend unavailable")
