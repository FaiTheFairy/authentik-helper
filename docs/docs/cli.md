# CLI

The `authentik-helper` CLI wraps the same Authentik operations as the web UI. It reads the same environment variables as the app.

- Use `--json` to output raw JSON instead of pretty tables.
- Use `serve` to run the web app via Uvicorn.

## Serve the app

```bash
# ASGI app from factory (recommended)
authentik-helper serve --factory --host 0.0.0.0 --port 8000
# or select an explicit ASGI target
authentik-helper serve --asgi "web.app_factory:create_app" --host 0.0.0.0 --port 8000
# enable reload for development
authentik-helper serve --factory --reload --log-level debug
```

## Show settings

```bash
authentik-helper settings
# JSON
authentik-helper --json settings
```

## Users

```bash
# Fetch a user by primary key (pk)
authentik-helper users get 42
```

## Groups

```bash
# List users in the Guests group
authentik-helper groups guests
# List users in the Members group
authentik-helper groups members
```

## Membership

```bash
# Guests → Members (also sends promotion email)
authentik-helper membership promote 123
# Skip email notification
authentik-helper membership promote 123 --no-email
# Members → Guests
authentik-helper membership demote 123
```

## Invites

```bash
# Create an invitation (sends email if --email provided)
authentik-helper invites create --email user@example.com --name "User Name"
```

- Invite link is generated from your `AK_BASE_URL` and `AK_INVITE_FLOW_SLUG`.
- Expiry defaults to `AK_INVITE_EXPIRES_DAYS`.

## Brand

```bash
# Show brand details from Authentik (uses AK_BRAND_UUID)
authentik-helper brand info
```

## Exit codes

- `0`: success
- `2`: usage error or missing required capability
