import tools.mailer as mail


def test_invitation_email_sends_starttls(monkeypatch):
    calls = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=30):
            calls["init"] = (host, port)

        def ehlo(self):
            calls["ehlo"] = calls.get("ehlo", 0) + 1

        def starttls(self):
            calls["starttls"] = True

        def login(self, user, pwd):
            calls["login"] = (user, pwd)

        def sendmail(self, from_addr, rcpts, msg):
            calls["sent"] = (from_addr, tuple(rcpts))
            calls["msg"] = msg

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP, raising=True)

    ok = mail.send_invitation_email(
        to_email="t@example.test",
        name="T",
        invite_url="https://x/if/flow?itoken=abc",
        expires_friendly="soon",
        org_name="org",
        external_url="https://x",
        footer="f",
    )
    assert ok is True
    assert calls["init"][1] != 465  # starttls path
    assert calls.get("starttls") is True
    assert "invite_url" not in calls.get(
        "msg", ""
    )  # template renders, but we don't assert body here


def test_promotion_email_sends_ssl_465(monkeypatch):
    calls = {}

    class FakeSMTPSsl:
        def __init__(self, host, port):
            calls["init_ssl"] = (host, port)

        def login(self, user, pwd):
            calls["login"] = (user, pwd)

        def sendmail(self, from_addr, rcpts, msg):
            calls["sent"] = (from_addr, tuple(rcpts))
            calls["msg"] = msg

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    # force port 465 for this test
    monkeypatch.setattr(mail.settings, "SMTP_PORT", 465, raising=False)
    monkeypatch.setattr(mail.smtplib, "SMTP_SSL", FakeSMTPSsl, raising=True)

    ok = mail.send_promotion_email(
        to_email="t@example.test",
        name="T",
        portal_url="https://portal",
        authentik_url="https://ak",
        org_name="Org",
        external_url="https://ext",
        footer="f",
    )
    assert ok is True
    assert calls["init_ssl"][1] == 465


def test_email_not_configured_returns_false(monkeypatch):
    # missing host or from -> False, no exception
    monkeypatch.setattr(mail.settings, "SMTP_HOST", "", raising=False)
    ok = mail.send_invitation_email(
        to_email="t@example.test",
        name="T",
        invite_url="https://x",
        expires_friendly="soon",
        org_name="org",
        external_url="https://x",
        footer="f",
    )
    assert ok is False
