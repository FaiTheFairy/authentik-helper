<!-- docs/getting-started.md -->
# Get started

## Create a limited Authentik account
Use a service user with an API token. It does not log in interactively and only needs these permissions:

- authentik_stages_invitation.add_invitation
- authentik_core.change_group
- authentik_core.view_user
- authentik_core.view_brand (optional, for branding)

## Requirements

- Python 3.11+ (recommend [uv](https://github.com/astral-sh/uv))
- Authentik instance + API token
- SMTP (optional, for emails)

## Configure environment

Set the following variables (for dev, export or use a `.env`):

- AK_BASE_URL, EXTERNAL_BASE_URL, AK_TOKEN
- AK_GUESTS_GROUP_UUID, AK_MEMBERS_GROUP_UUID, AK_INVITE_FLOW_SLUG
- SESSION_SECRET (required)
- OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET (required unless `DISABLE_AUTH=true`)

## Run locally

```bash
uv sync --dev
uv run authentik-helper serve --factory --host 127.0.0.1 --port 8000
```
Now open http://127.0.0.1:8000.

## Run with Docker

```bash
docker build -t authentik-helper .
docker run --rm -p 8000:8000 --env-file .env authentik-helper
```
Or use `docker-compose.yml.example`.

## Reverse proxy and hosts

- Set standard X-Forwarded-* headers. TLS should terminate at the proxy.
- `TrustedHostMiddleware` allows `localhost` and the host from `EXTERNAL_BASE_URL`.

## Health checks

- GET `/healthz` → `{ "ok": true }`

## Sessions

- Cookies are `secure` when `EXTERNAL_BASE_URL` starts with `https://`.
- Always set a strong `SESSION_SECRET`.

## Next steps

- Sign in, create an invite, promote a guest.
