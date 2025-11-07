from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from fastapi import FastAPI
from jinja2 import Environment
from pydantic import AnyHttpUrl, PositiveInt

from services.brand import brand_ctx
from tools.settings import settings
from web.templates import templates as _templates

logger = logging.getLogger("authentik_helper.mail")


# templates


def _get_jinja() -> Environment:
    return _templates.env


def _render_html(template_name: str, context: Dict[str, Any]) -> str:
    tpl = _get_jinja().get_template(template_name)
    return tpl.render(**context)


# smtp


def _smtp_settings() -> (
    tuple[Optional[str], PositiveInt, Optional[str], Optional[str], Optional[str]]
):
    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    user = settings.SMTP_USERNAME
    pwd = (
        settings.SMTP_PASSWORD.get_secret_value()
        if hasattr(settings.SMTP_PASSWORD, "get_secret_value") and settings.SMTP_PASSWORD
        else None
    )
    from_addr = settings.SMTP_FROM
    return host, port, user, pwd, from_addr


def _send_html(to_email: str, subject: str, html_body: str) -> bool:
    host, port, user, pwd, from_addr = _smtp_settings()
    logger.info(
        "smtp_attempt",
        extra={
            "host": host,
            "port": port,
            "from": from_addr,
            "to": to_email,
            "auth": bool(user and pwd),
        },
    )
    if not host or not from_addr:
        logger.warning("smtp_not_configured", extra={"missing": ["SMTP_HOST_or_SMTP_FROM"]})
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port) as s:
                if user and pwd:
                    s.login(user, pwd)
                s.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.ehlo()
                s.starttls()
                s.ehlo()
                if user and pwd:
                    s.login(user, pwd)
                s.sendmail(from_addr, [to_email], msg.as_string())
        return True
    except Exception as e:
        logger.error("smtp_send_failed", extra={"error": str(e)}, exc_info=True)
        return False


# brand defaults helper


def _brand_defaults(app: Optional[FastAPI] = None) -> Dict[str, Any]:
    """
    returns {'org_name','portal_url','brand_logo','brand_favicon'}
    prefers warmed app.state.brand when app is provided, otherwise cached brand_ctx()
    """
    defaults = brand_ctx(app)
    # ensure keys always exist
    return {
        "org_name": defaults.get("org_name") or getattr(settings, "ORGANIZATION_NAME", ""),
        "portal_url": defaults.get("portal_url") or getattr(settings, "PORTAL_URL", ""),
        "brand_logo": defaults.get("brand_logo") or "",
    }


# public api


def send_invitation_email(
    *,
    to_email: str,
    name: str,
    invite_url: str,
    expires_friendly: str,
    org_name: Optional[str] = None,
    external_url: str | AnyHttpUrl | None = None,
    footer: str = "",
    brand_logo: Optional[str] = None,
    app: Optional[FastAPI] = None,
) -> bool:
    """
    render and send the invitation email (templates/invitation_email.html)

    inputs:
      - to_email, name, invite_url, expires_friendly
      - org_name / external_url (optional; defaults pulled from brand/settings)
      - footer (optional)
      - brand_logo (optional; falls back to brand)
      - app (optional fastapi app to reuse warmed brand data)
    """
    b = _brand_defaults(app)
    org = org_name or b["org_name"] or "our service"
    ext = external_url or getattr(settings, "EXTERNAL_BASE_URL", None)
    logo = brand_logo or b["brand_logo"]

    html = _render_html(
        "invitation_email.html",
        {
            "name": name or "",
            "invite_url": invite_url,
            "expires_friendly": expires_friendly,
            "org_name": org,
            "external_url": ext,
            "footer": footer,
            "brand_logo": logo,
        },
    )
    subject = settings.EMAIL_SUBJECT_INVITATION or f"Your invite to {org}!"
    return _send_html(to_email, subject, html)


def send_promotion_email(
    *,
    to_email: str,
    name: str,
    portal_url: str | AnyHttpUrl | None = None,
    authentik_url: str | AnyHttpUrl,
    org_name: Optional[str] = None,
    external_url: str | AnyHttpUrl | None = None,
    footer: str = "",
    brand_logo: Optional[str] = None,
    app: Optional[FastAPI] = None,
) -> bool:
    """
    render and send the promotion email (templates/promotion_email.html)

    inputs:
      - to_email, name
      - portal_url (optional; falls back to brand portal or authentik_url)
      - authentik_url (fallback if portal undefined)
      - org_name / external_url (optional; defaults pulled from brand/settings)
      - footer (optional)
      - brand_logo (optional; falls back to brand)
      - app (optional fastapi app to reuse warmed brand data)
    """
    b = _brand_defaults(app)
    portal = portal_url or b["portal_url"] or str(authentik_url)
    org = org_name or b["org_name"] or portal or "our service"
    ext = external_url or getattr(settings, "EXTERNAL_BASE_URL", None)
    logo = brand_logo or b["brand_logo"]

    html = _render_html(
        "promotion_email.html",
        {
            "name": name or "",
            "portal_url": portal,
            "org_name": org,
            "external_url": ext,
            "footer": footer,
            "brand_logo": logo,
        },
    )
    subject = settings.EMAIL_SUBJECT_PROMOTION or f"You've been promoted on {org}!"
    return _send_html(to_email, subject, html)
