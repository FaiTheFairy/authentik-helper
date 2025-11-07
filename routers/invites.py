# routers/invites.py
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends

from tools.mailer import send_invitation_email
from tools.settings import settings
from core.auth import require_user
from core.utils import redact_email
from services.authentik import ak

logger = logging.getLogger("authentik_helper.app")

# protect every route in this module with auth
router = APIRouter(dependencies=[Depends(require_user)])


@router.post("/invites")
def post_invite(payload: Dict[str, Any] = Body(...)):
    """
    create an invitation via authentik and optionally send an email.
    - 'name', 'username', and 'email' are optional.
    - if 'email' is present and an invite url is returned, an email is sent.
    """
    logger.info(
        "invites_create_requested",
        extra={
            "has_flow": bool(payload.get("flow")),
            "name_set": bool(payload.get("name")),
            "email_set": bool(payload.get("email")),
        },
    )

    raw_name = (payload.get("name") or "").strip()
    raw_username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip().lower()

    # default username: prefer explicit username, then name, then local part of email
    username = (
        raw_username or raw_name or (email.split("@", 1)[0] if email and "@" in email else "")
    )
    name = raw_name or username

    flow_override = (payload.get("flow") or "").strip()
    single_use = bool(payload.get("single_use", True))
    expires_days = payload.get("expires_days")

    inv = ak.create_invitation(
        name=name,
        username=username,
        email=email,
        single_use=single_use,
        expires_days=(int(expires_days) if isinstance(expires_days, (int, float)) else None),
        flow_slug=flow_override or None,
    )

    invite_url = inv.get("invite_url") or ""
    expires_friendly = inv.get("expires_friendly") or ""

    # mail is best-effort: log and continue on failure
    try:
        if email and invite_url:
            sent = send_invitation_email(
                to_email=email,
                name=name,
                invite_url=invite_url,
                expires_friendly=expires_friendly,
                org_name=settings.ORGANIZATION_NAME,
                external_url=settings.EXTERNAL_BASE_URL,
                footer=settings.EMAIL_FOOTER,
            )
            if sent:
                logger.info("invitation_email_sent", extra={"email": redact_email(email)})
            else:
                logger.warning("invitation_email_not_sent", extra={"email": redact_email(email)})
    except Exception as e:
        logger.warning(
            "invitation_email_failed",
            extra={"email": redact_email(email), "error": str(e)},
        )

    return inv
