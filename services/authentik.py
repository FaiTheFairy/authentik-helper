# services/authentik.py
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from tools.settings import settings


class AuthentikClient:
    """client for authentik api v3"""

    def __init__(self) -> None:
        self._session: Optional[httpx.Client] = None
        self._base = str(settings.AK_BASE_URL).rstrip("/")

    def _get_session(self) -> httpx.Client:
        if self._session is None:
            s = httpx.Client()
            token = (
                settings.AK_TOKEN.get_secret_value()
                if hasattr(settings.AK_TOKEN, "get_secret_value")
                else str(settings.AK_TOKEN)
            )
            s.headers.update(
                {
                    "authorization": f"Bearer {token}",
                    "accept": "application/json",
                    "content-type": "application/json",
                    "user-agent": "authentik-helper/1.x",
                }
            )

            self._session = s
        return self._session

    def _url(self, path: str) -> str:
        p = path if path.startswith("/") else f"/{path}"
        return f"{self._base}/api/v3{p}"

    def _get(self, path: str, **params: Any) -> Any:
        r = self._get_session().get(self._url(path), params=params or {})
        if r.status_code != 200:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise RuntimeError(f"GET {path} -> {r.status_code}: {detail}")
        return r.json()

    def _post(self, path: str, payload: Dict[str, Any]) -> httpx.Response:
        return self._get_session().post(self._url(path), json=payload)

    @staticmethod
    def _iso_utc_in(days: int) -> str:
        d = max(1, int(days))
        dt = datetime.now(timezone.utc) + timedelta(days=d)
        return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    @staticmethod
    def _friendly_from_iso(iso_str: str) -> str:
        s = (iso_str or "").strip()
        if not s:
            return ""
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.strftime("%a, %b %d, %Y, %I:%M %p UTC")
        except Exception:
            return s

    def list_group_users(self, group_uuid: str) -> Dict[str, Any]:
        data = self._get(f"/core/groups/{group_uuid}/", include_users="true")
        group_name = data.get("name") or ""
        users: List[Dict[str, Any]] = []
        if isinstance(data, dict) and isinstance(data.get("users_obj"), list):
            users = [u for u in data["users_obj"] if isinstance(u, dict)]
        elif isinstance(data, dict) and isinstance(data.get("users"), list):
            for pk in data["users"]:
                try:
                    users.append(self.get_user(int(pk)))
                except Exception:
                    pass
        users.sort(key=lambda u: int(u.get("pk") or u.get("id") or 0))
        return {
            "group_name": group_name,
            "users": [
                {
                    "pk": u.get("pk") or u.get("id"),
                    "username": u.get("username") or u.get("name") or "",
                    "email": u.get("email") or "",
                }
                for u in users
            ],
        }

    def get_user(self, pk: int) -> Dict[str, Any]:
        return self._get(f"/core/users/{int(pk)}/")

    def switch_group_user_pk(
        self, source_group_uuid: str, target_group_uuid: str, user_pk: int
    ) -> Dict[str, int]:
        add_r = self._post(f"/core/groups/{target_group_uuid}/add_user/", {"pk": int(user_pk)})
        rm_r = self._post(f"/core/groups/{source_group_uuid}/remove_user/", {"pk": int(user_pk)})

        def _code(resp: httpx.Response) -> int:
            try:
                _ = resp.json()
            except Exception:
                _ = resp.text  # noqa: F841
            return resp.status_code

        add_code = _code(add_r)
        rm_code = _code(rm_r)

        ok = (200, 201, 202, 204)
        if add_code not in ok or rm_code not in ok:
            try:
                add_body = add_r.json()
            except Exception:
                add_body = add_r.text
            try:
                rm_body = rm_r.json()
            except Exception:
                rm_body = rm_r.text
            raise RuntimeError(
                f"switch failed add={add_code}:{add_body} remove={rm_code}:{rm_body}"
            )

        return {"add": add_code, "remove": rm_code}

    def create_invitation(
        self,
        name: str | None = None,
        username: str | None = None,
        email: str | None = None,
        single_use: bool = True,
        expires_days: Optional[int] = None,
        flow_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        days = settings.AK_INVITE_EXPIRES_DAYS if expires_days is None else int(expires_days)
        expires_iso = self._iso_utc_in(days)
        payload: Dict[str, Any] = {
            "name": name or f"invite-{uuid.uuid4().hex[:8]}",
            "single_use": bool(single_use),
            "expires": expires_iso,
            "fixed_data": {"name": name, "username": username, "email": email},
        }
        r = self._post("/stages/invitation/invitations/", payload)
        try:
            inv = r.json()
        except Exception:
            inv = {"raw": r.text}
        if r.status_code not in (200, 201, 202, 204):
            raise RuntimeError(f"invite create failed {r.status_code}: {inv}")
        token = inv.get("pk")
        slug = (flow_slug or settings.AK_INVITE_FLOW_SLUG or "").strip()
        if not slug:
            raise RuntimeError("invite flow slug is not configured")
        inv["invite_url"] = f"{self._base}/if/flow/{slug}/?itoken={token}"
        inv["expires_friendly"] = self._friendly_from_iso(inv.get("expires") or expires_iso)
        return inv

    def search_users(self, q: str, limit: int = 25) -> Dict[str, Any]:
        limit = max(1, min(int(limit), 100))
        data = self._get("/core/users/", search=q, page_size=limit)
        results = data.get("results", data if isinstance(data, list) else [])
        users = [
            {
                "pk": u.get("pk") or u.get("id"),
                "username": (u.get("username") or u.get("name") or "") or "",
                "email": u.get("email") or "",
                "name": u.get("name") or "",
            }
            for u in results
        ]
        return {"query": q, "users": users}

    def brand_info(self, brand_uuid: str) -> Dict[str, Any]:
        data = self._get(f"/core/brands/{brand_uuid}/")
        title = data.get("branding_title") or data.get("name") or ""
        domain = data.get("domain") or ""
        logo_path = data.get("branding_logo") or ""
        base = self._base.rstrip("/")
        logo = f"{base}/{logo_path.lstrip('/')}" if logo_path else ""
        return {
            "brand_name": title,
            "brand_domain": domain,
            "brand_logo": logo,
        }


ak = AuthentikClient()
