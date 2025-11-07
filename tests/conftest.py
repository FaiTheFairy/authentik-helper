# tests/conftest.py

import os
import importlib
import pytest
from starlette.testclient import TestClient

# set env before any app imports so settings singleton picks these up
os.environ.update(
    {
        "AK_BASE_URL": "https://ak.example.test",
        "EXTERNAL_BASE_URL": "https://helper.example.test",
        "AK_TOKEN": "dummy",
        "AK_GUESTS_GROUP_UUID": "guests-uuid",
        "AK_MEMBERS_GROUP_UUID": "members-uuid",
        "AK_INVITE_FLOW_SLUG": "invite-via-email",
        "AK_INVITE_EXPIRES_DAYS": "7",
        "SMTP_HOST": "smtp.example.test",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "user",
        "SMTP_PASSWORD": "pass",
        "SMTP_FROM": "noreply@example.test",
        "PORTAL_URL": "https://portal.example.test",
        "ORGANIZATION_NAME": "example org",
        "EMAIL_FOOTER": "test footer",
        "SESSION_SECRET": "supersecret",
        "OIDC_ISSUER": "https://issuer.example.test/",
        "OIDC_CLIENT_ID": "cid",
        "OIDC_CLIENT_SECRET": "csecret",
        "OIDC_SCOPES": "openid profile email",
        "LOG_LEVEL": "WARNING",
        "DISABLE_AUTH": "true",  # skip oidc during tests
    }
)

# reload settings to ensure it read the env above if tests are re-run
import tools.settings as settings_mod

importlib.reload(settings_mod)  # rebuilds the singleton inside module


@pytest.fixture(scope="session")
def app():
    # import here after env is set
    from web.app_factory import create_app

    return create_app("Authentik Helper")


@pytest.fixture()
def client(app):
    # critical: do not follow redirects so tests can assert 302/303
    return TestClient(app, base_url="http://localhost", follow_redirects=False)
