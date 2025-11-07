<!-- docs/index.md -->
# Authentik Helper

An admin UI and API focused on three jobs: create invites, promote guests to members, and demote members back to guests. It wraps Authentik’s API with a clean, minimal workflow.

## Features

- Invite creation: name, username, email, single-use, expiry days; smart username defaults from name/email.
- Membership actions: promote/demote individually or in bulk with clear per-user results.
- Email templates: branded HTML invitation and promotion emails via SMTP.
- Secure by default: OIDC login, trusted hosts, secure cookies on HTTPS, minimal logging.
- PWA niceties: manifest and service worker endpoints.

## Stack

- FastAPI, Authlib (OIDC), httpx, Jinja2, Pydantic Settings

## Quick links

- Get started: [getting-started.md](getting-started.md)
- Configuration: [configuration.md](configuration.md)
- CLI: [cli.md](cli.md) • HTTP API: [api.md](api.md) • Emails: [emails.md](emails.md)
- Guides: [invites](guides/invites.md), [membership](guides/membership.md)
