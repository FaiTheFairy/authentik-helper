# tests/test_auth_enabled.py
import importlib
import pytest
from fastapi.testclient import TestClient


def _reload_settings_and_auth():
    from tools import settings as settings_mod

    importlib.reload(settings_mod)
    # make core.auth rebind to the (new) settings instance
    import core.auth as auth_mod

    importlib.reload(auth_mod)


@pytest.fixture()
def auth_enabled_env(monkeypatch):
    # turn auth ON for these tests and reload dependent modules
    monkeypatch.setenv("DISABLE_AUTH", "false")
    _reload_settings_and_auth()
    try:
        yield
    finally:
        # restore auth OFF for the rest of the suite and reload again
        monkeypatch.setenv("DISABLE_AUTH", "true")
        _reload_settings_and_auth()


def _build_app():
    from web.app_factory import create_app

    return create_app("Authentik Helper")


@pytest.fixture()
def client_auth_enabled(auth_enabled_env):
    # fresh app/client with auth enabled, and no redirect following by default
    app = _build_app()
    return TestClient(app, base_url="http://localhost")


def test_me_redirects_when_not_logged_in(client_auth_enabled):
    r = client_auth_enabled.get("/me", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers.get("location") == "/login"


def test_root_redirects_to_login_when_auth_enabled(client_auth_enabled):
    r = client_auth_enabled.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers.get("location") == "/login"
