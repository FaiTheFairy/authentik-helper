# tests/test_public_routes.py
from types import CellType


def test_homepage_renders(client):
    r = client.get("/", follow_redirects=False)
    # when auth is enabled the root redirects to /login; otherwise it renders html.
    if r.status_code in (302, 303):
        assert r.headers.get("location") == "/login"
        return
    assert r.status_code == 200
    ctype = r.headers.get("content-type", "")
    assert "text/html" in ctype


def test_login_page_renders(client):
    # app serves a login page even if auth is disabled
    r = client.get("/login")
    # allow either ok or redirect (some auth setups 302 to provider)
    assert r.status_code in (200, 302, 303)


def test_logout_redirects(client):
    r = client.get("/logout")
    assert r.status_code in (302, 303)


def test_404_error_shape(client):
    r = client.get("/this-path-does-not-exist")
    assert r.status_code == 404
    # error handler should return html or json
    assert r.text
