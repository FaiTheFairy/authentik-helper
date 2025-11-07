# Authentik Helper

Documentation: https://faithefairy.github.io/authentik-helper

Admin UI and API for three jobs with Authentik: create invites, promote guests to members, and demote members to guests. It wraps Authentik’s API with a focused workflow, HTML emails, and a small CLI.

## Features

- Invitations: create single-use links with name/username/email, expiry days; uses your Authentik invite flow.
- Membership: promote/demote users individually or in bulk, with optional promotion email.
- Emails: branded HTML invitation and promotion emails via SMTP (Jinja templates).
- Login: OIDC login (Authlib). Set `DISABLE_AUTH=true` for local testing only.
- Safety: trusted hosts derived from `EXTERNAL_BASE_URL`, signed cookie sessions, concise logs with `X-Request-Id`.
- PWA: manifest and service worker endpoints.
- CLI: same operations from the terminal.

<video src="demo.mp4" controls width="380"></video>

## Requirements

- Python 3.11+ (recommend [uv](https://github.com/astral-sh/uv)) or Docker
- Authentik instance with a service user + API token
- Groups for Guests and Members, and an invitation flow in Authentik

Recommended Authentik permissions for the service user:

- `authentik_stages_invitation.add_invitation`
- `authentik_core.change_group`
- `authentik_core.view_user`
- `authentik_core.view_brand` (optional, for branding)

## Quick start (uv)

```bash
uv sync
# create and fill a .env as below
uv run authentik-helper serve --factory --host 0.0.0.0 --port 8000
# open http://127.0.0.1:8000
```

`.env` example (adjust values):

```dotenv
# Core
AK_BASE_URL=https://auth.example.com
EXTERNAL_BASE_URL=https://helper.example.com
AK_TOKEN=your_api_token
AK_GUESTS_GROUP_UUID=uuid-for-guests
AK_MEMBERS_GROUP_UUID=uuid-for-members
AK_INVITE_FLOW_SLUG=invite-via-email

# Sessions / auth
SESSION_SECRET=please-change-me
OIDC_ISSUER=https://issuer.example.com/
OIDC_CLIENT_ID=client-id
OIDC_CLIENT_SECRET=client-secret
# For quick local testing only (don’t use in prod):
# DISABLE_AUTH=true

# Optional email
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=user
SMTP_PASSWORD=pass
SMTP_FROM=noreply@example.com

# Optional branding
AK_BRAND_UUID=
ORGANIZATION_NAME=Example Org
PORTAL_URL=https://portal.example.com
BRAND_LOGO=https://example.com/logo.png
```

## Quick start (Docker)

```bash
docker build -t authentik-helper .
docker run --rm -p 8000:8000 --env-file .env authentik-helper
```

Or use `docker-compose.yml.example`.

## Configuration

- Full list of required/optional settings and how branding is merged: see `docs/docs/configuration.md`.
- Health check: `GET /healthz` → `{ "ok": true }`.
- Secure cookies are enabled automatically when `EXTERNAL_BASE_URL` starts with `https://`.

## CLI

```bash
# Show settings (pretty or JSON)
authentik-helper settings
authentik-helper --json settings

# Groups
authentik-helper groups guests
authentik-helper groups members

# Membership
authentik-helper membership promote 123       # sends email by default
authentik-helper membership promote 123 --no-email
authentik-helper membership demote 123

# Invites
authentik-helper invites create --email user@example.com --name "User Name"

# Brand info (uses AK_BRAND_UUID)
authentik-helper brand info
```

More examples: `docs/docs/cli.md` and `docs/docs/api.md`.

## Development

```bash
uv sync --dev
uv run authentik-helper serve --factory --reload --port 8000
uv run pytest
```

Project layout:

```
core/  routers/  services/  tools/  web/  tests/
```

- Error and transport failures become clean JSON (500/502) via error handlers.
- Middleware adds request IDs and writes concise logs (see `logs/app.ndjson`).
- Footer build info comes from baked metadata, env, or git.

## Overriding templates

All HTML (site pages and emails) lives under `web/templates/`. You can modify these files or mount a volume in Docker to override them.

## FAQ

- What happens if I demote myself? You will likely lose access to apps restricted to Members. This can lock you out of Authentik-Helper and, depending on your Authentik setup, its homepage. Use caution.

## License

MIT
