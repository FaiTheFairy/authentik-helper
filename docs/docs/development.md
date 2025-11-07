<!-- docs/development.md -->
# Development

Use uv for a smooth setup, run tests, and keep a tight feedback loop.

## Setup

```bash
uv sync --dev
```

## Run

```bash
# Web app via CLI (ASGI factory)
uv run authentik-helper serve --factory --reload --port 8000
# Or raw Uvicorn
uv run uvicorn app:app --reload --port 8000
```

## Test

```bash
uv run pytest
```

## Project layout

```
authentik-helper/
  app.py
  core/
  routers/
  services/
  tools/
  web/          # templates, static assets, PWA manifest & sw
  tests/
```

## Notes

- Error handlers return clean JSON for runtime/transport issues.
- Middleware adds a per-request ID, access logs, and `X-Request-Id`.
- Branding is cached and merged with settings at startup.
- Footer build info comes from baked metadata, env, or git.
