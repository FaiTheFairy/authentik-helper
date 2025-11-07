import importlib
from starlette.testclient import TestClient


def test_rejects_untrusted_host(monkeypatch):
    # simulate "not configured": remove var (empty string fails pydantic URL validation)
    monkeypatch.delenv("EXTERNAL_BASE_URL", raising=False)
    import tools.settings as settings_mod

    importlib.reload(settings_mod)  # rebuild Settings()
    import web.app_factory as app_factory_mod

    importlib.reload(app_factory_mod)  # rebind imported `settings`

    app = app_factory_mod.create_app("Authentik Helper")
    # evil host should be blocked by TrustedHostMiddleware
    c = TestClient(app, base_url="http://evil.test", follow_redirects=False)
    r = c.get("/")
    assert r.status_code == 400  # invalid host header


def test_allows_external_host(monkeypatch):
    monkeypatch.setenv("EXTERNAL_BASE_URL", "https://helper.example.test:8443")
    import tools.settings as settings_mod

    importlib.reload(settings_mod)
    import web.app_factory as app_factory_mod

    importlib.reload(app_factory_mod)

    app = app_factory_mod.create_app("Authentik Helper")
    c = TestClient(app, base_url="http://helper.example.test:8443", follow_redirects=False)
    r = c.get("/healthz")
    assert r.status_code == 200
