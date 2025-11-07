# tools/demo/mock_authentik.py
# Minimal fake Authentik-like API for demos/screenshots.

from __future__ import annotations
import random
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from faker import Faker

fake = Faker()
app = FastAPI(title="Mock Authentik (demo)", version="0.0.2")


# in-memory data models
class User(BaseModel):
    pk: int
    uuid: str
    username: str
    name: str
    email: str
    is_active: bool = True
    groups: List[str] = []


class Group(BaseModel):
    uuid: str
    name: str
    slug: str


# seed data
NUM_USERS = 1200
START_PK = 1

groups: Dict[str, Group] = {}
users: Dict[int, User] = {}

# create two main groups: guests, members
guests_uuid = str(uuid.uuid4())
members_uuid = str(uuid.uuid4())
groups[guests_uuid] = Group(uuid=guests_uuid, name="Guests", slug="guests")
groups[members_uuid] = Group(uuid=members_uuid, name="Members", slug="members")

# generate fake users
for i in range(START_PK, START_PK + NUM_USERS):
    username = fake.user_name()
    name = fake.name()
    email = f"{username}@example.test"
    g = [members_uuid] if random.random() < 0.30 else [guests_uuid]
    users[i] = User(
        pk=i, uuid=str(uuid.uuid4()), username=username, name=name, email=email, groups=g
    )


# helpers
def find_user_by_pk(pk: int) -> User:
    u = users.get(pk)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u


def group_exists(group_uuid: str) -> bool:
    return group_uuid in groups


# brand
@app.get("/api/v3/core/brands/{brand_uuid}/")
async def brand_info(brand_uuid: str):
    # minimal brand shape expected by app
    return {
        "brand_name": "Demo Org",
        "brand_domain": "demo.example.test",
        "brand_logo": "",
        "brand_favicon": "",
    }


# groups
@app.get("/api/v3/core/groups/")
async def list_groups():
    return {"count": len(groups), "results": [g.model_dump() for g in groups.values()]}


# support /api/v3/core/groups/{uuid}/?include_users=true
@app.get("/api/v3/core/groups/{group_uuid}/")
async def group_detail(group_uuid: str, include_users: Optional[bool] = False):
    if not group_exists(group_uuid):
        raise HTTPException(404, "group not found")
    g = groups[group_uuid].model_dump()
    if include_users:
        members = [u for u in users.values() if group_uuid in u.groups]
        g["users_obj"] = [u.model_dump() for u in members]
    return g


# Existing: separate “users listing” under a group (kept for completeness)
@app.get("/api/v3/core/groups/{group_uuid}/users/")
async def group_users(group_uuid: str, limit: int = 50, offset: int = 0):
    if not group_exists(group_uuid):
        raise HTTPException(404, "group not found")
    members = [u for u in users.values() if group_uuid in u.groups]
    total = len(members)
    return {"count": total, "results": [u.model_dump() for u in members[offset : offset + limit]]}


# Add/remove membership (accept pk in multiple field names)
@app.post("/api/v3/core/groups/{target_group_uuid}/add_user/")
async def add_user_to_group(target_group_uuid: str, payload: Dict):
    if not group_exists(target_group_uuid):
        raise HTTPException(404, "group not found")
    pk = payload.get("id") or payload.get("pk") or payload.get("user_pk")
    if pk is None:
        raise HTTPException(400, "missing user id")
    u = find_user_by_pk(int(pk))
    if target_group_uuid not in u.groups:
        u.groups.append(target_group_uuid)
    return {"ok": True, "user": u.model_dump()}


@app.post("/api/v3/core/groups/{target_group_uuid}/remove_user/")
async def remove_user_from_group(target_group_uuid: str, payload: Dict):
    if not group_exists(target_group_uuid):
        raise HTTPException(404, "group not found")
    pk = payload.get("id") or payload.get("pk") or payload.get("user_pk")
    if pk is None:
        raise HTTPException(400, "missing user id")
    u = find_user_by_pk(int(pk))
    if target_group_uuid in u.groups:
        u.groups = [g for g in u.groups if g != target_group_uuid]
    return {"ok": True, "user": u.model_dump()}


# users
@app.get("/api/v3/core/users/")
async def list_users(limit: int = 50, offset: int = 0):
    all_users = list(users.values())
    return {
        "count": len(all_users),
        "results": [u.model_dump() for u in all_users[offset : offset + limit]],
    }


@app.get("/api/v3/core/users/{pk}/")
async def get_user(pk: int):
    return find_user_by_pk(pk)


@app.get("/api/v3/core/users/search/")
async def search_users(q: str = Query(..., min_length=1), limit: int = 25):
    ql = q.lower()
    found = [
        u
        for u in users.values()
        if ql in u.name.lower() or ql in u.username.lower() or ql in u.email.lower()
    ]
    return {"count": len(found), "results": [u.model_dump() for u in found[:limit]]}


# invites
class InviteCreate(BaseModel):
    name: str
    username: str
    email: str
    single_use: Optional[bool] = True
    expires_days: int = 7
    flow: Optional[str] = None


@app.post("/api/v3/core/invites/")
async def create_invite(inv: InviteCreate):
    token = str(uuid.uuid4())
    expires = (datetime.now(timezone.utc) + timedelta(days=inv.expires_days)).isoformat()
    link = f"https://demo.example.test/if/{inv.flow or 'default'}/?itoken={token}"
    return {"pk": token, "invite_url": link, "expires": expires}


# health/auth convenience
@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/login")
async def login():
    return {"login": "mock login page (demo)"}


@app.get("/login/oidc")
async def login_oidc():
    return {"oidc": "start"}


@app.get("/auth/callback")
async def auth_callback():
    return {"ok": True}


# direct promote/demote helpers
class BulkAction(BaseModel):
    pks: List[int]
    send_mail: Optional[bool] = False


@app.post("/promote")
async def promote_one(payload: Dict):
    pk = int(payload.get("pk"))  # type: ignore
    send_mail = bool(payload.get("send_mail", False))
    u = find_user_by_pk(pk)
    if members_uuid not in u.groups:
        u.groups = [g for g in u.groups if g != guests_uuid] + [members_uuid]
    return {"ok": True, "user": u.model_dump(), "sent_email": send_mail}


@app.post("/demote")
async def demote_one(payload: Dict):
    pk = int(payload.get("pk"))  # type: ignore
    u = find_user_by_pk(pk)
    if guests_uuid not in u.groups:
        u.groups = [g for g in u.groups if g != members_uuid] + [guests_uuid]
    return {"ok": True, "user": u.model_dump()}


@app.post("/promote/bulk")
async def promote_bulk(payload: BulkAction):
    results = []
    for pk in payload.pks:
        try:
            u = find_user_by_pk(pk)
            if members_uuid not in u.groups:
                u.groups = [g for g in u.groups if g != guests_uuid] + [members_uuid]
            results.append({"pk": pk, "ok": True})
        except Exception as e:
            results.append({"pk": pk, "ok": False, "detail": str(e)})
    return {
        "count_ok": sum(1 for r in results if r["ok"]),
        "count_failed": sum(1 for r in results if not r["ok"]),
        "results": results,
    }


@app.post("/demote/bulk")
async def demote_bulk(payload: BulkAction):
    results = []
    for pk in payload.pks:
        try:
            u = find_user_by_pk(pk)
            if guests_uuid not in u.groups:
                u.groups = [g for g in u.groups if g != members_uuid] + [guests_uuid]
            results.append({"pk": pk, "ok": True})
        except Exception as e:
            results.append({"pk": pk, "ok": False, "detail": str(e)})
    return {
        "count_ok": sum(1 for r in results if r["ok"]),
        "count_failed": sum(1 for r in results if not r["ok"]),
        "results": results,
    }


# Convenience: expose the mock group UUIDs
@app.get("/demo/_group-uuids")
async def demo_group_uuids():
    return {"guests_uuid": guests_uuid, "members_uuid": members_uuid}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("tools.demo.mock_authentik:app", host="0.0.0.0", port=8001, reload=True)
