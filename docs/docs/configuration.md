<!-- docs/configuration.md -->
# Configuration

Set configuration through **environment variables**. The app uses typed settings (Pydantic), so you’ll get clear errors if something is missing (hopefully).

---

## Required settings

| Variable | Type | Description |
| --- | --- | --- |
| **AK_BASE_URL** | AnyHttpUrl | Authentik base URL, e.g. `https://auth.example.com` |
| **EXTERNAL_BASE_URL** | AnyHttpUrl | Public URL of this app (cookies, redirects) |
| **AK_TOKEN** | SecretStr | Authentik API token with needed scopes |
| **AK_GUESTS_GROUP_UUID** | str | UUID of your Guests group |
| **AK_MEMBERS_GROUP_UUID** | str | UUID of your Members group |
| **SESSION_SECRET** | SecretStr | Session secret for cookies. Generate via `openssl rand -base64 32` |

---

## Optional settings

| Variable | Type | Default | What it does |
| --- | --- | --- | --- |
| **AK_BRAND_UUID** | str \| None | `None` | Authentik brand to pull name/logo from |
| **AK_INVITE_FLOW_SLUG** | str \| None | `None` | Invite flow slug (uses your AK flow if set) |
| **AK_INVITE_EXPIRES_DAYS** | int | `7` | Days until invite expires |
| **SMTP_HOST** | str \| None | `None` | SMTP server |
| **SMTP_PORT** | PositiveInt | `465` | SMTP port |
| **SMTP_USERNAME** | str \| None | `None` | SMTP username |
| **SMTP_PASSWORD** | SecretStr \| None | `None` | SMTP password |
| **SMTP_FROM** | str \| None | `None` | From address for emails |
| **PORTAL_URL** | AnyHttpUrl \| None | `None` | Overrides portal URL shown in emails/UI over the domain from Authentik's brand. |
| **ORGANIZATION_NAME** | str \| None | `None` | Overrides org name grabbed from Authentik brand. |
| **BRAND_LOGO** | str \| None | `None` | Overrides org logo as grabbed from Authentik brand. |
| **EMAIL_SUBJECT_INVITATION** | str \| None | `None` | Subject override for invite email. Default subject is "Your invite to {org}!"x<sup>*</sup>|
| **EMAIL_SUBJECT_PROMOTION** | str \| None | `None` | Subject override for promotion email. Default subject is "You've been promoted on {org}!"<sup>*</sup> |
| **EMAIL_FOOTER** | str | `"Sent using Authentik Helper. Built with love."` | Footer text in emails |
| **OIDC_ISSUER**<sup>*</sup> | AnyHttpUrl \| None | `None` | OIDC issuer (enables login) |
| **OIDC_CLIENT_ID**<sup>*</sup> | str \| None | `None` | OIDC client ID |
| **OIDC_CLIENT_SECRET**<sup>*</sup> | SecretStr \| None | `None` | OIDC client secret |
| **OIDC_SCOPES**<sup>*</sup> | str | `"openid profile email"` | Space-separated scopes |
| **LOG_LEVEL** | `"DEBUG" \| "INFO" \| "WARNING" \| "ERROR" \| "CRITICAL"` | `"INFO"` | Log level|
| **DISABLE_AUTH** | bool | `False` | Disable OIDC and trust everyone (not for prod) |

<sup>*</sup>OIDC settings are required unless `DISABLE_AUTH=true`.

---

## How branding works

The app merges **settings** with **Authentik brand** values (if `AK_BRAND_UUID` is set):

1. It fetches **brand name**, **portal URL**, and **logo/favicon** from Authentik.
2. Your explicit settings **override** the brand.
3. Templates use the merged result.
