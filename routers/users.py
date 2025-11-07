# routers/users.py
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from tools.settings import settings
from core.auth import require_user
from services.authentik import ak

logger = logging.getLogger("authentik_helper.app")

# everything here requires an authenticated session
router = APIRouter(dependencies=[Depends(require_user)])


@router.get("/me")
def me(user: dict = Depends(require_user)):
    """return the current session user dict"""
    return user


@router.get("/guest-users")
def guest_users():
    """list users in the guests group"""
    return ak.list_group_users(settings.AK_GUESTS_GROUP_UUID)


@router.get("/members-users")
def member_users():
    """list users in the members group"""
    return ak.list_group_users(settings.AK_MEMBERS_GROUP_UUID)


@router.get("/search-users")
def search_users(q: str = "", limit: int = 25):
    """simple user search proxy with a small guard for empty queries"""
    limit = max(1, min(int(limit or 25), 100))
    q = (q or "").strip()
    if not q:
        return {"query": q, "users": []}
    result = ak.search_users(q, limit)
    logger.info("user_search", extra={"q": q, "results": len(result.get("users", []))})
    return result
