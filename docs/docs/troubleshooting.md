<!-- docs/troubleshooting.md -->
# Troubleshooting

## I get redirected to `/login`

You’re not signed in, or `DISABLE_AUTH` is `false`. Configure **OIDC** or set `DISABLE_AUTH=true` **only** for local testing.

---

## `401` or `403` errors

Your **API token** is missing or lacks scope. Check `AK_TOKEN` and token permissions.

---

## Invites don’t send email

Confirm **SMTP** settings. Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM`. Check logs.

---

## Bulk promote/demote returns partial failures

This is normal if some users can’t move (wrong group or missing user). The response includes **per-user results** with `ok` and `detail`. Fix the bad rows and retry.

---

## Brand logo isn’t showing

Set `AK_BRAND_UUID` or provide `ORGANIZATION_NAME`, `BRAND_LOGO` and `PORTAL_URL`. You can override logos explicitly in settings or templates.

## How do I show my avatar (as admin)?

Ensure that your avatar is passed to the userinfo endpoint as `picture` under the `profile` scope. You can do this in Authentik by creating a new property mapping (Admin Interface -> Customization -> Property Mappings), setting the `Scope name` to "picture" and adding the following expression:

```python
url = request.user.attributes.get("avatar")
return {"picture": url} if url else {}
```
