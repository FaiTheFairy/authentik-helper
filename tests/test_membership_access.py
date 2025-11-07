import importlib
import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client_auth_on(monkeypatch):
    # turn auth ON for these tests and rebuild settings/auth
    monkeypatch.setenv("DISABLE_AUTH", "false")
    import tools.settings as settings_mod
    import core.auth as auth_mod

    importlib.reload(settings_mod)
    importlib.reload(auth_mod)

    from web.app_factory import create_app

    app = create_app("Authentik Helper")
    return TestClient(app, base_url="http://localhost", follow_redirects=False)


def test_promote_requires_auth_when_enabled(client_auth_on):
    r = client_auth_on.post("/promote", json={"pk": 1})
    # test for either blocking users (401) OR redirecting unauthenticated
    # users to /login
    assert r.status_code in (401, 302, 303)
    if r.status_code in (302, 303):
        assert r.headers.get("location") == "/login"


def test_demote_requires_auth_when_enabled(client_auth_on):
    r = client_auth_on.post("/demote", json={"pk": 1})
    assert r.status_code in (401, 302, 303)
    if r.status_code in (302, 303):
        assert r.headers.get("location") == "/login"
