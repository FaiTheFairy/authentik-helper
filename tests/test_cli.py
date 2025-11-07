# tests/test_cli.py
# pytest for tools/cli.py where mailer is imported at module top-level

import io
import json
import sys
import types
import pytest

import tools.cli as cli


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Provide a minimal settings object with required attributes."""
    s = types.SimpleNamespace(
        AK_BASE_URL="https://auth.example.com",
        EXTERNAL_BASE_URL="https://portal.example.com",
        AK_GUESTS_GROUP_UUID="guests-uuid",
        AK_MEMBERS_GROUP_UUID="members-uuid",
        AK_BRAND_UUID="brand-uuid",
        AK_INVITE_FLOW_SLUG="flow-slug",
        AK_INVITE_EXPIRES_DAYS=7,
        ORGANIZATION_NAME="Fairyland",
        PORTAL_URL="https://portal.example.com",
        EMAIL_FOOTER="Sent with love.",
    )
    monkeypatch.setattr(cli, "_settings", lambda: s)
    return s


@pytest.fixture
def calls(monkeypatch):
    """Patch the top-level imported `mailer` in tools.cli, recording calls."""
    recorder = types.SimpleNamespace(
        sent_invites=[],
        sent_promos=[],
    )

    def send_invitation_email(**kw):
        recorder.sent_invites.append(kw)
        return True

    def send_promotion_email(**kw):
        recorder.sent_promos.append(kw)
        return True

    fake_mailer = types.SimpleNamespace(
        send_invitation_email=send_invitation_email,
        send_promotion_email=send_promotion_email,
    )
    # Patch the imported module symbol
    monkeypatch.setattr(cli, "mailer", fake_mailer, raising=True)
    return recorder


@pytest.fixture
def fake_ak(monkeypatch):
    """Mock Authentik client that `cli._ak()` returns."""
    ak = types.SimpleNamespace(
        get_user=lambda pk: {
            "pk": pk,
            "username": f"user{pk}",
            "name": f"User {pk}",
            "email": f"user{pk}@example.com",
            "is_active": True,
            "last_login": "2025-10-29T00:00:00Z",
        },
        list_group_users=lambda group_uuid: [
            {
                "pk": 1,
                "username": "guest1",
                "name": "Guest One",
                "email": "g1@example.com",
                "is_active": True,
            },
            {
                "pk": 2,
                "username": "guest2",
                "name": "Guest Two",
                "email": "g2@example.com",
                "is_active": True,
            },
        ],
        switch_group_user_pk=lambda src, dst, pk: {"src": src, "dst": dst, "pk": pk},
        create_invitation=lambda **kw: {
            "token": "abc123",
            "name": kw.get("name", "invite-user"),
            "invite_url": "https://auth.example.com/invite/abc123",
            "expires": "2025-11-06T00:00:00Z",
        },
        brand_info=lambda brand_uuid: {
            "name": "Fairyland",
            "domain": "example.com",
            "logo": "https://example.com/logo.png",
        },
    )
    monkeypatch.setattr(cli, "_ak", lambda: ak)
    return ak


def run_cli(args):
    """Capture stdout from cli.main(args)."""
    buf, old = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        cli.main(args)
    finally:
        sys.stdout = old
    return buf.getvalue()


# Tests


def test_settings_table(fake_ak):
    out = run_cli(["settings"])
    assert "AK_BASE_URL" in out
    assert "https://auth.example.com" in out


def test_settings_json(fake_ak):
    out = run_cli(["--json", "settings"])
    data = json.loads(out)
    assert isinstance(data, dict)
    assert data["AK_BASE_URL"] == "https://auth.example.com"


def test_users_get(fake_ak):
    out = run_cli(["users", "get", "1"])
    assert "User 1" in out
    assert "user1@example.com" in out


def test_groups_guests(fake_ak):
    out = run_cli(["groups", "guests"])
    assert "guest1" in out and "guest2" in out


def test_membership_promote_sends_email(fake_ak, calls):
    out = run_cli(["membership", "promote", "123"])
    # Pretty output contains "promote"
    assert "promote" in out
    # Mailer recorded exactly one promotion email
    assert len(calls.sent_promos) == 1
    promo = calls.sent_promos[0]
    assert promo["to_email"] == "user123@example.com"
    assert promo["name"] == "User 123"


def test_membership_demote(fake_ak, calls):
    out = run_cli(["membership", "demote", "2"])
    assert "demote" in out
    # Demote should NOT send a promo email
    assert len(calls.sent_promos) == 0


def test_invites_create_sends_email_and_prints_arg(fake_ak, calls):
    out = run_cli(["invites", "create", "--email", "test@example.com", "--name", "Tester"])
    # Pretty table should include the provided email (from args, not API)
    assert "test@example.com" in out
    # One invitation email sent
    assert len(calls.sent_invites) == 1
    inv = calls.sent_invites[0]
    assert inv["to_email"] == "test@example.com"
    # Should include invite_url from service response
    assert inv["invite_url"].startswith("https://auth.example.com/invite/")


def test_brand_info(fake_ak):
    out = run_cli(["brand", "info"])
    assert "Fairyland" in out
    assert "example.com" in out
