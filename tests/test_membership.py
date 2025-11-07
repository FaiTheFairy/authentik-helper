# tests/test_membership.py
def test_promote_ok_sends_mail(monkeypatch, client):
    import services.authentik as svc

    def fake_switch_group_user_pk(*args, **kwargs):
        return {"add": 200, "remove": 200}

    monkeypatch.setattr(svc.ak, "switch_group_user_pk", fake_switch_group_user_pk)
    monkeypatch.setattr(
        svc.ak, "get_user", lambda *a, **k: {"email": "u@example.test", "name": "U"}
    )

    import tools.mailer as mail

    monkeypatch.setattr(mail, "send_promotion_email", lambda **k: True)

    r = client.post("/promote", json={"pk": 42, "send_mail": True})
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_demote_ok(monkeypatch, client):
    import services.authentik as svc

    monkeypatch.setattr(svc.ak, "switch_group_user_pk", lambda *a, **k: {"add": 200, "remove": 200})

    r = client.post("/demote", json={"pk": 7})
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_promote_bulk_mixtures(monkeypatch, client):
    import services.authentik as svc

    def fake_switch(*args, **kwargs):
        pk = args[-1] if args else kwargs.get("pk", 0)
        return {"add": 200, "remove": 200} if pk % 2 == 0 else {"add": 500, "remove": 500}

    monkeypatch.setattr(svc.ak, "switch_group_user_pk", fake_switch)

    import routers.membership as membership_router

    monkeypatch.setattr(membership_router, "send_promotion_email", lambda **k: True)

    monkeypatch.setattr(
        svc.ak,
        "get_user",
        lambda *a, **k: {"email": f"u{k.get('pk', args[-1])}@example.test", "name": "n"},
    )

    r = client.post("/promote/bulk", json={"pks": [1, 2, 3, 4], "send_mail": True})
    assert r.status_code == 200
    j = r.json()
    assert j["count_ok"] == 2
    assert j["count_failed"] == 2


def kwargs_or_args_pk(*a, **k):
    return k.get("pk", (a[-1] if a else None))
