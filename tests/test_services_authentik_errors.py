import types
import services.authentik as svc


class _Resp:
    def __init__(self, code=200, json_data=None, text=None):
        self.status_code = code
        self._json = {} if json_data is None else json_data
        self.text = "" if text is None else text

    def json(self):
        return self._json


def test__get_raises_on_non_200(monkeypatch):
    def _fake_get(url, params=None, timeout=None):
        return _Resp(code=503, json_data={"err": "x"})

    sess = types.SimpleNamespace(get=_fake_get)
    monkeypatch.setattr(svc.AuthentikClient, "_get_session", lambda self: sess, raising=True)
    c = svc.AuthentikClient()
    try:
        c._get("/core/users/1/")
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "GET" in str(e) and "503" in str(e)


def test_switch_group_user_pk_raises_on_non_ok(monkeypatch):
    def _fake_post(url, json=None, timeout=None):
        return _Resp(code=500, json_data={"bad": True})

    sess = types.SimpleNamespace(post=_fake_post)
    monkeypatch.setattr(svc.AuthentikClient, "_get_session", lambda self: sess, raising=True)
    c = svc.AuthentikClient()
    try:
        c.switch_group_user_pk("g1", "g2", 7)
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "switch failed" in str(e)


def test_create_invitation_missing_flow_slug(monkeypatch):
    # success response but no flow slug configured -> raises
    def _fake_post(url, json=None, timeout=None):
        return _Resp(code=200, json_data={"pk": "abc", "expires": "2026-01-01T00:00:00Z"})

    sess = types.SimpleNamespace(post=_fake_post)
    monkeypatch.setattr(svc.AuthentikClient, "_get_session", lambda self: sess, raising=True)
    monkeypatch.setattr(svc.settings, "AK_INVITE_FLOW_SLUG", "", raising=False)
    c = svc.AuthentikClient()
    try:
        c.create_invitation(name="n", email="e@example", username="u")
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "flow slug" in str(e)


def test_list_group_users_legacy_users_field(monkeypatch):
    # legacy shape: users list of pks -> get_user is called
    def _fake_get(self, path, **params):
        if path.startswith("/core/groups/"):
            return {"name": "Guests", "users": [1]}
        raise AssertionError("unexpected path")

    monkeypatch.setattr(svc.AuthentikClient, "_get", _fake_get, raising=True)
    monkeypatch.setattr(
        svc.AuthentikClient,
        "get_user",
        lambda self, pk: {"pk": pk, "email": "e", "username": "u"},
        raising=True,
    )
    out = svc.AuthentikClient().list_group_users("uuid")
    assert out["group_name"] == "Guests"
    assert out["users"][0]["pk"] == 1


def test_time_helpers_are_sane():
    s = svc.AuthentikClient._iso_utc_in(0)  # clamps >=1 day
    assert s.endswith("Z") and "T" in s
    assert svc.AuthentikClient._friendly_from_iso("bad") == "bad"
