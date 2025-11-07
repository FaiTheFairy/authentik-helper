from fastapi.responses import RedirectResponse
import routers.public as public


class _FakeOIDCOK:
    server_metadata = {"end_session_endpoint": "https://idp.example/logout"}

    async def authorize_redirect(self, request, cb_url):
        return RedirectResponse("https://idp.example/authorize?cb=" + cb_url)

    async def authorize_access_token(self, request):
        return {"access_token": "tok"}

    async def userinfo(self, token):
        return {"sub": "1", "email": "a@example.test", "name": "Alice", "picture": "p"}


class _FakeOIDCUserinfoError(_FakeOIDCOK):
    async def userinfo(self, token):
        raise RuntimeError("userinfo failed")


class _FakeOIDCNoEndSession(_FakeOIDCOK):
    server_metadata = {}  # exercise branch without end_session_endpoint


def test_login_oidc_redirect(client, monkeypatch):
    monkeypatch.setattr(public, "get_oidc", lambda: _FakeOIDCOK(), raising=True)
    r = client.get("/login/oidc")
    assert r.status_code in (302, 303, 307)
    assert "https://idp.example/authorize" in r.headers.get("location", "")


def test_auth_callback_sets_session_and_redirects(client, monkeypatch):
    monkeypatch.setattr(public, "get_oidc", lambda: _FakeOIDCOK(), raising=True)
    r = client.get("/auth/callback")
    assert r.status_code in (302, 303)
    assert r.headers.get("location") == "/"


def test_auth_callback_handles_userinfo_error(client, monkeypatch):
    monkeypatch.setattr(public, "get_oidc", lambda: _FakeOIDCUserinfoError(), raising=True)
    r = client.get("/auth/callback")
    assert r.status_code in (302, 303, 307)
    assert r.headers.get("location") == "/"


def test_logout_uses_end_session_when_available(client, monkeypatch):
    monkeypatch.setattr(public, "get_oidc", lambda: _FakeOIDCOK(), raising=True)
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code in (302, 303, 307)
    loc = r.headers.get("location", "")
    assert "https://idp.example/logout" in loc
    assert "post_logout_redirect_uri=" in loc


def test_logout_redirects_home_when_no_end_session(client, monkeypatch):
    monkeypatch.setattr(public, "get_oidc", lambda: _FakeOIDCNoEndSession(), raising=True)
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers.get("location") == "/"
