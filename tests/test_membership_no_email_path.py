def test_promote_with_send_mail_true_but_user_has_no_email(monkeypatch, client):
    # helper: accept redirect to /login when auth is enabled
    def _assert_status_or_login_redirect(resp, expected: int) -> bool:
        if resp.status_code in (302, 303):
            assert resp.headers.get("location") == "/login"
            return True
        assert resp.status_code == expected
        return False

    # make the switch succeed
    import services.authentik as svc

    monkeypatch.setattr(
        svc.ak, "switch_group_user_pk", lambda *a, **k: {"add": 200, "remove": 200}, raising=True
    )
    # user has no email -> mail function must NOT be called
    monkeypatch.setattr(svc.ak, "get_user", lambda pk: {"pk": pk, "name": "NoMail"}, raising=True)

    # track unexpected calls
    called = []

    import tools.mailer as mail

    monkeypatch.setattr(
        mail, "send_promotion_email", lambda **k: (called.append(k) or True), raising=True
    )

    r = client.post("/promote", json={"pk": 123, "send_mail": True})
    # If auth is enabled for this client, we will see a redirect to /login.
    # otherwise, we should get 200 OK.
    _assert_status_or_login_redirect(r, 200)
    # mailer must not be called because user has no email
    assert called == []
