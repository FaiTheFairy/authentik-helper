# core/auth.py
from __future__ import annotations

from fastapi import HTTPException, Request
from tools.settings import settings


def require_user(request: Request) -> dict:
    """require a logged-in session; short-circuit if auth is disabled"""
    if settings.DISABLE_AUTH:
        # stub user for local runs / tests
        return {"sub": "dev", "email": "dev@example.com", "name": "Developer"}

    user = request.session.get("user")
    if not user:
        # use 303 so browsers do a GET to /login
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user
