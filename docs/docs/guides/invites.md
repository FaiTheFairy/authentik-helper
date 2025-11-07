<!-- docs/guides/invites.md -->
# Invites

Use the Invites panel to bring new people into your Authentik setup.

## Create an invite

1. Fill out:
   - Name — full name
   - Username — login name in Authentik
   - Email — where the invite will be sent
   - Expiry days — how long the invite is valid
   - Single use — if the link should work only once
2. Click Create Invitation.

## What gets sent

- Email includes your brand name, logo, and a button to continue.
- A plain link is included as a fallback.
- The link stops working once the invite expires or has been used.

## Prefilled fields

When an invitation is created the helper passes fixed values (`name`, `username`, and `email`) into Authentik's invitation stage. If your Authentik invite flow reads these fixed fields, the registration form presented to the recipient will be pre-filled with the provided name, username, and email.

## Acknowledgements

Prefilled invitation behavior was inspired by work from stiw47: https://github.com/goauthentik/authentik/discussions/13305#discussioncomment-13094337
