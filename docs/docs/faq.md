<!-- docs/faq.md -->
# FAQ

## Do I need OIDC?
No, but you should use it. If you set `DISABLE_AUTH=true`, the app trusts every request. That’s for local tests, not production.

---

## Can I customize the emails?
Yes. Adjust **subjects**, **footer**, and **brand** via settings. Tweak the Jinja templates at `web/templates/*`.

---

## How do I see logs?
Watch `logs/app.ndjson` or stdout. Each response includes an **`X-Request-Id`** header to trace logs.

---

## What happens if Authentik is down?
The app returns **502** for transport failures and **500** for unexpected errors. Check `/healthz` and your Authentik status page.

---

## What happens when I demote myself?
That depends on the user logged in and their permissions on Authentik. You will be demoted into the guest user and lose your access to applications provided only for the members. This WILL lock you out of Authentik-Helper, and may cause loss of access to Authentik’s homepage if you are not a super user, permission is given to you via a group association, and you demoted yourself from said group.
