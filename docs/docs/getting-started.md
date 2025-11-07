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

Pull the published image from GitHub Container Registry and run it locally:

```bash
# pull latest (or replace 'latest' with a specific tag, e.g. 'v0.1.0')
docker pull ghcr.io/faithefairy/authentik-helper:latest
docker run --rm -p 8000:8000 --env-file .env ghcr.io/faithefairy/authentik-helper:latest
```

Or use the provided `docker-compose.yml.example` (it already references the GHCR image):

```bash
docker compose -f docker-compose.yml.example up
```

## Reverse proxy and hosts

- Set standard X-Forwarded-\* headers. TLS should terminate at the proxy.
- `TrustedHostMiddleware` allows `localhost` and the host from `EXTERNAL_BASE_URL`.

## Health checks

- GET `/healthz` → `{ "ok": true }`

## Sessions

- Cookies are `secure` when `EXTERNAL_BASE_URL` starts with `https://`.
- Always set a strong `SESSION_SECRET`.

## Next steps

- Sign in, create an invite, promote a guest.
