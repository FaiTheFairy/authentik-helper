import importlib
import types
import pytest


def _reload_security_with(monkeypatch, disable_auth: bool):
    monkeypatch.setenv("DISABLE_AUTH", "true" if disable_auth else "false")
    import tools.settings as settings_mod

    importlib.reload(settings_mod)
    import core.security as sec

    importlib.reload(sec)
    return sec


def test_get_oidc_raises_when_disabled(monkeypatch):
    sec = _reload_security_with(monkeypatch, disable_auth=True)
    with pytest.raises(Exception) as e:
        sec.get_oidc()
    # FastAPI HTTPException(503)
    assert getattr(e.value, "status_code", None) == 503


def test_get_oidc_raises_when_not_registered(monkeypatch):
    sec = _reload_security_with(monkeypatch, disable_auth=False)
    # overwrite the global oauth to an object lacking 'oidc'
    sec.oauth = types.SimpleNamespace()
    with pytest.raises(Exception) as e:
        sec.get_oidc()
    assert getattr(e.value, "status_code", None) == 503


def test_oauth_has_oidc_when_enabled(monkeypatch):
    sec = _reload_security_with(monkeypatch, disable_auth=False)
    # registration is local-only; should expose .oidc attribute
    assert hasattr(sec.oauth, "oidc")
