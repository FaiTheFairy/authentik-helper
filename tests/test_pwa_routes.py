# tests/test_pwa_routes.py
def test_manifest(client):
    r = client.get("/manifest.webmanifest")
    assert r.status_code == 200
    ctype = r.headers.get("content-type", "")
    # fastapi/starlette may serve as json or webmanifest (both ok)
    assert "json" in ctype or "webmanifest" in ctype
    j = r.json()
    assert "name" in j or "short_name" in j


def test_service_worker(client):
    r = client.get("/sw.js")
    assert r.status_code == 200
    ctype = r.headers.get("content-type", "")
    assert "javascript" in ctype
    assert "self" in r.text
