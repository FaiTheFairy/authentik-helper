<!-- docs/security-privacy.md -->
# Security & Privacy

Protect your users. Keep secrets out of logs. Run behind TLS.

---

## What the app stores

- **Session** data in a signed cookie (no server-side session store).
- **No** user data is persisted beyond requests.

---

## Recommended settings

- Set a **strong `SESSION_SECRET`**.
- Use **HTTPS** for your `EXTERNAL_BASE_URL` so cookies are **secure**.
- Use a dedicated account in Authentik and limit its **API token scopes**.

---

## Email safety

Emails use your **brand** and include only what’s needed: **name**, **invite link**, and **footer**. Email addresses are **redacted** in logs.
