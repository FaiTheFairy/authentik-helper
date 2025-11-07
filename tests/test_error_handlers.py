# tests/test_error_handlers.py
from fastapi import APIRouter, Query


def test_uncaught_exception_500(client, app):
    # register a throwy route dynamically to hit 500 handler
    router = APIRouter()

    @router.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    app.include_router(router)

    r = client.get("/boom")
    assert r.status_code == 500
    # error handler formats either json or html; ensure body present
    assert r.text


def test_validation_422_uses_error_handler(app, client):
    # adds a route that requires an int to trigger 422 validation
    router = APIRouter()

    @router.get("/needs-int")
    def needs_int(x: int = Query(...)):
        return {"x": x}

    app.include_router(router)

    r = client.get("/needs-int?x=not-an-int")
    # Starlette will 422; the custom handler should still respond with a body
    assert r.status_code == 422
    assert r.text
