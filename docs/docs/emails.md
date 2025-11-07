# Emails

The app can send two kinds of HTML emails via SMTP:

- Invitation: `web/templates/invitation_email.html`
- Promotion: `web/templates/promotion_email.html`

Templates are Jinja and accept these variables:

- Invitation: `name`, `invite_url`, `expires_friendly`, `org_name`, `external_url`, `footer`, `brand_logo`
- Promotion: `name`, `portal_url`, `org_name`, `external_url`, `footer`, `brand_logo`

## SMTP settings

- `SMTP_HOST` (required to send)
- `SMTP_PORT` (default `465` for SMTPS)
- `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`

If `SMTP_HOST` or `SMTP_FROM` is missing, sending is skipped and a warning is logged.

## Subjects

- `EMAIL_SUBJECT_INVITATION` (default: `Your invite to {org}!`)
- `EMAIL_SUBJECT_PROMOTION` (default: `You've been promoted on {org}!`)

## Branding

Brand defaults come from Authentik when `AK_BRAND_UUID` is set. You can override with settings:

- `ORGANIZATION_NAME`
- `PORTAL_URL`
- `BRAND_LOGO`

## Overriding templates

Mount or edit the Jinja files in `web/templates/` to customize wording and styles.
