# HTTP API

Authenticated routes require a logged-in session unless `DISABLE_AUTH=true`.

## Health

- GET `/healthz` → `{ "ok": true }`

## Auth

- GET `/login` → Login page (always available)
- GET `/login/oidc` → Starts OIDC authorization code flow
- GET `/auth/callback` → Completes login, stores session, redirects to `/`
- GET `/logout` → Clears session; if provider exposes `end_session_endpoint`, redirects there with `post_logout_redirect_uri`

## Session

- GET `/me` → current user session

Example

```json
{
  "sub": "42",
  "email": "user@example.com",
  "name": "User",
  "picture": "https://.../avatar.png"
}
```

## Users

- GET `/guest-users` → users in `AK_GUESTS_GROUP_UUID`
- GET `/members-users` → users in `AK_MEMBERS_GROUP_UUID`
- GET `/search-users?q=neo&limit=25` → lightweight search proxy

Shapes

```json
// group listing
{
  "group_name": "Guests",
  "users": [
    {"pk": 1, "username": "alpha", "email": "a@example.test"}
  ]
}

// search
{
  "query": "neo",
  "users": [
    {"pk": 9, "username": "neo", "email": "n@example.test", "name": "Neo"}
  ]
}
```

## Membership

- POST `/promote` → move user Guests → Members
- POST `/demote` → move user Members → Guests
- POST `/promote/bulk` → promote multiple `pks` (optionally send email)
- POST `/demote/bulk` → demote multiple `pks`

Requests

```json
// promote one
{"pk": 123, "send_mail": true}

// demote one
{"pk": 123}

// bulk promote
{"pks": [1,2,3], "send_mail": true}

// bulk demote
{"pks": [1,2,3]}
```

Responses

```json
// single
{"status": "ok", "add": 200, "remove": 200}

// bulk
{
  "count_ok": 2,
  "count_failed": 1,
  "results": [
    {"pk": 1, "ok": true,  "detail": {"add": 200, "remove": 200}},
    {"pk": 2, "ok": false, "detail": "..."}
  ]
}
```

## Invites

- POST `/invites` → create invitation; optionally sends email when `email` provided and an invite URL is returned.

Request

```json
{
  "name": "Ada",
  "username": "ada",
  "email": "ada@example.test",
  "single_use": true,
  "expires_days": 7,
  "flow": "invite-via-email"
}
```

Response

```json
{
  "pk": "abc123",
  "invite_url": "https://auth.example/if/flow/invite-via-email/?itoken=abc123",
  "expires": "2030-01-01T00:00:00Z",
  "expires_friendly": "Tue, Jan 01, 2030, 12:00 AM UTC"
}
```

## PWA assets

- GET `/manifest.webmanifest` → PWA manifest
- GET `/sw.js` → Service worker (no-cache)

## Errors

- Transport failures → `502 {"detail": "backend unavailable"}`
- Unhandled exceptions → `500 {"detail": "backend unavailable"}`
- Validation errors → `422` with JSON body
