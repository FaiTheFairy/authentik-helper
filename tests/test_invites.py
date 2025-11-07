# tests/test_invites.py
def test_create_invite_with_email_sends_mail(monkeypatch, client):
    fake_inv = {
        "pk": "abc123",
        "invite_url": "https://ak.example.test/if/flow/invite-via-email/?itoken=abc123",
        "expires": "2025-09-09T00:00:00Z",
        "expires_friendly": "Tue, Sep 09, 2025, 12:00 AM UTC",
    }

    import services.authentik as svc

    monkeypatch.setattr(svc.ak, "create_invitation", lambda *a, **k: dict(fake_inv))

    import routers.invites as invites_router

    monkeypatch.setattr(invites_router, "send_invitation_email", lambda **k: True)

    payload = {
        "name": "Ada",
        "username": "ada",
        "email": "ada@example.test",
        "single_use": True,
        "expires_days": 5,
        "flow": "invite-via-email",
    }
    r = client.post("/invites", json=payload)
    assert r.status_code == 200
    j = r.json()
    assert j["pk"] == "abc123"
    assert j["invite_url"].startswith("https://ak.example.test/")
