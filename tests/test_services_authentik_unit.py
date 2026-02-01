# tests/test_services_authentik_unit.py
# unit-level tests for services/authentik.py without real network

import json
import re
import types

import services.authentik as svc


class FakeResp:
    def __init__(self, status_code=200, json_data=None, text=None):
        self.status_code = status_code
        self._json = {} if json_data is None else json_data
        self.text = json.dumps(self._json) if text is None else text

    def json(self):
        return self._json


def _fake_requests_responder(method, url, **kwargs):
    m = method.upper()

    # GET /api/v3/core/groups/{uuid}/?include_users=true
    if (
        m == "GET"
        and re.search(r"/api/v3/core/groups/[^/]+/?$", url)
        and (kwargs.get("params") or {}).get("include_users") == "true"
    ):
        is_guests = "guests" in url or "uuid-guests" in url
        return 200, {
            "name": "Guests" if is_guests else "Members",
            "users_obj": [
                {"pk": 1, "username": "alpha", "email": "a@example.test"},
                {"pk": 2, "username": "beta", "email": "b@example.test"},
            ],
        }

    # GET /api/v3/core/users/42/
    if m == "GET" and re.search(r"/api/v3/core/users/\d+/?$", url):
        return 200, {"pk": 42, "username": "zaphod", "email": "u@example.test", "name": "Zaphod"}

    # GET /api/v3/core/users/?search=...
    if m == "GET" and re.search(r"/api/v3/core/users/?$", url):
        # client sends params {'search': '...','page_size': N}
        search = (kwargs.get("params") or {}).get("search", "")
        # shape mirrors the real api enough for  parser
        return 200, {"results": [], "count": 0, "query_echo": search}

    # POST /api/v3/core/groups/{uuid}/add_user/  or  .../remove_user/
    if m == "POST" and re.search(r"/api/v3/core/groups/.+/(add_user|remove_user)/?$", url):
        return 200, {"status": "ok"}

    # POST /api/v3/stages/invitation/invitations/
    if m == "POST" and re.search(r"/api/v3/stages/invitation/invitations/?$", url):
        return 201, {"pk": "abc123", "expires": "2030-01-01T00:00:00Z"}

    return 404, {"detail": "not found"}


def _monkeypatch_transport(monkeypatch):
    import httpx
    import services.authentik as svc

    class FakeResp:
        def __init__(self, status_code=200, json_data=None, text=None):
            self.status_code = status_code
            self._json = {} if json_data is None else json_data
            self.text = json.dumps(self._json) if text is None else text

        def json(self):
            return self._json

    def _fake_requests_responder(method, url, **kwargs):
        m = method.upper()
        if (
            m == "GET"
            and re.search(r"/api/v3/core/groups/[^/]+/?$", url)
            and (kwargs.get("params") or {}).get("include_users") == "true"
        ):
            is_guests = "guests" in url or "uuid-guests" in url
            return 200, {
                "name": "Guests" if is_guests else "Members",
                "users_obj": [
                    {"pk": 1, "username": "alpha", "email": "a@example.test"},
                    {"pk": 2, "username": "beta", "email": "b@example.test"},
                ],
            }
        if m == "GET" and re.search(r"/api/v3/core/users/\d+/?$", url):
            return 200, {
                "pk": 42,
                "username": "zaphod",
                "email": "u@example.test",
                "name": "Zaphod",
            }
        if m == "GET" and re.search(r"/api/v3/core/users/?$", url):
            search = (kwargs.get("params") or {}).get("search", "")
            return 200, {"results": [], "count": 0, "query_echo": search}
        if m == "POST" and re.search(r"/api/v3/core/groups/.+/(add_user|remove_user)/?$", url):
            return 200, {"status": "ok"}
        if m == "POST" and re.search(r"/api/v3/stages/invitation/invitations/?$", url):
            return 201, {"pk": "abc123", "expires": "2030-01-01T00:00:00Z"}
        return 404, {"detail": "not found"}

    class _FakeClient:
        def __init__(self):
            self.headers = {}

        def get(self, url, params=None):
            code, payload = _fake_requests_responder("GET", url, params=params or {})
            return FakeResp(status_code=code, json_data=payload)

        def post(self, url, json=None):
            code, payload = _fake_requests_responder("POST", url, json=json or {})
            return FakeResp(status_code=code, json_data=payload)

    monkeypatch.setattr(httpx, "Client", lambda *a, **k: _FakeClient(), raising=True)

    # important: drop any previously-created real session so the fake is used
    svc.ak._session = None


def test_list_group_users(monkeypatch):
    _monkeypatch_transport(monkeypatch)
    out = svc.ak.list_group_users("uuid-guests")
    assert out["group_name"] == "Guests"
    assert isinstance(out["users"], list) and out["users"]


def test_get_user(monkeypatch):
    _monkeypatch_transport(monkeypatch)
    out = svc.ak.get_user(42)
    assert out["email"] == "u@example.test"


def test_search_users(monkeypatch):
    _monkeypatch_transport(monkeypatch)
    out = svc.ak.search_users(q="neo", limit=10)
    assert out["query"] == "neo"


def test_switch_group_user_pk_add_and_remove(monkeypatch):
    _monkeypatch_transport(monkeypatch)
    res_add = svc.ak.switch_group_user_pk("src", "dst", 7)
    assert res_add.get("status") == "ok" or "add" in res_add or "remove" in res_add


def test_create_invitation(monkeypatch):
    _monkeypatch_transport(monkeypatch)
    out = svc.ak.create_invitation(
        flow_slug="invite-via-email", email="a@example.test", name="A", username="A"
    )
    assert "invite_url" in out and out["invite_url"].startswith("https://")


def test_create_invitation_uses_slug(monkeypatch):
    import httpx
    import services.authentik as svc

    recorded = {}

    class FakeResp:
        def __init__(self, status_code=201, json_data=None, text=None):
            self.status_code = status_code
            self._json = {} if json_data is None else json_data
            self.text = json.dumps(self._json) if text is None else text

        def json(self):
            return self._json

    class RecordingClient:
        def __init__(self):
            self.headers = {}

        def get(self, url, params=None):
            return FakeResp(status_code=200, json_data={})

        def post(self, url, json=None):
            recorded['url'] = url
            recorded['json'] = json or {}
            return FakeResp(status_code=201, json_data={"pk": "abc123", "expires": "2030-01-01T00:00:00Z"})

    monkeypatch.setattr(httpx, "Client", lambda *a, **k: RecordingClient(), raising=True)

    svc.ak._session = None

    out = svc.ak.create_invitation(
        flow_slug="invite-via-email", email="john@example.test", name="John Smith", username="jsmith"
    )

    assert recorded.get('json', {}).get('name') == 'john-smith'
    assert recorded.get('json', {}).get('fixed_data', {}).get('name') == 'John Smith'
    assert "invite_url" in out and out["invite_url"].startswith("https://")
