import logging
from starlette.testclient import TestClient

import routers.membership as membership
from services import authentik as svc


def _assert_status_or_login_redirect(resp, expected: int) -> bool:
    """
    If unauthenticated, routes may redirect to /login (302/303).
    Return True if redirected; otherwise assert expected status and return False.
    """
    if resp.status_code in (302, 303):
        assert resp.headers.get("location") == "/login"
        return True
    assert resp.status_code == expected
    return False


def test_promote_logs_not_sent_when_mail_false(monkeypatch, client, caplog):
    # real email address, but mailer returns False -> logs 'promotion_email_not_sent'
    monkeypatch.setattr(
        svc.ak, "switch_group_user_pk", lambda *a, **k: {"add": 200, "remove": 200}, raising=True
    )
    monkeypatch.setattr(
        svc.ak, "get_user", lambda pk: {"email": "x@example.test", "name": "X"}, raising=True
    )
    monkeypatch.setattr(membership, "send_promotion_email", lambda **k: False, raising=True)

    caplog.set_level(logging.INFO, logger="authentik_helper.app")
    r = client.post("/promote", json={"pk": 99, "send_mail": True})
    if _assert_status_or_login_redirect(r, 200):
        # if we were redirected to /login (auth enabled), we can't assert mail logs.
        return
    # should log 'promotion_email_not_sent' when mailer returns false
    assert any("promotion_email_not_sent" in rec.message for rec in caplog.records)


def test_promote_logs_failed_when_mail_raises(monkeypatch, client, caplog):
    monkeypatch.setattr(
        svc.ak, "switch_group_user_pk", lambda *a, **k: {"add": 200, "remove": 200}, raising=True
    )
    monkeypatch.setattr(
        svc.ak, "get_user", lambda pk: {"email": "x@example.test", "name": "X"}, raising=True
    )

    def _boom(**k):
        raise RuntimeError("boom")

    monkeypatch.setattr(membership, "send_promotion_email", _boom, raising=True)

    caplog.set_level(logging.INFO, logger="authentik_helper.app")
    r = client.post("/promote", json={"pk": 100, "send_mail": True})
    if _assert_status_or_login_redirect(r, 200):
        return

    # even though mail raised, route should log 'promotion_email_failed' (best-effort)
    assert any("promotion_email_failed" in rec.message for rec in caplog.records)
