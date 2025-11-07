# routers/membership.py
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException

from tools.mailer import send_promotion_email
from tools.settings import settings
from core.auth import require_user
from core.utils import redact_email
from services.authentik import ak

logger = logging.getLogger("authentik_helper.app")

# require auth for everything here
router = APIRouter(dependencies=[Depends(require_user)])


@router.post("/promote")
def promote(payload: Dict[str, Any] = Body(...)):
    """move a user from guests to members and optionally send a notification email"""
    pk = payload.get("pk")
    if pk is None:
        raise HTTPException(status_code=400, detail="pk is required")
    try:
        pk_i = int(pk)
    except Exception:
        raise HTTPException(status_code=400, detail="pk must be an integer")

    send_mail = bool(payload.get("send_mail", True))

    result = ak.switch_group_user_pk(
        settings.AK_GUESTS_GROUP_UUID,
        settings.AK_MEMBERS_GROUP_UUID,
        pk_i,
    )

    if send_mail:
        # best-effort mail; never fail the promote because of smtp
        try:
            u = ak.get_user(pk_i)
            to_email = (u.get("email") or "").strip()
            name = (u.get("name") or u.get("username") or "").strip()
            if to_email:
                sent = send_promotion_email(
                    to_email=to_email,
                    name=name,
                    portal_url=settings.PORTAL_URL,
                    authentik_url=settings.AK_BASE_URL,
                    org_name=settings.ORGANIZATION_NAME,
                    external_url=settings.EXTERNAL_BASE_URL,
                    footer=settings.EMAIL_FOOTER,
                )
                if sent:
                    logger.info(
                        "promotion_email_sent",
                        extra={"email": redact_email(to_email), "pk": pk_i},
                    )
                else:
                    logger.warning(
                        "promotion_email_not_sent",
                        extra={"email": redact_email(to_email), "pk": pk_i},
                    )
        except Exception as e:
            logger.warning("promotion_email_failed", extra={"pk": pk_i, "error": str(e)})

    return {"status": "ok", **result}


@router.post("/demote")
def demote(payload: Dict[str, Any] = Body(...)):
    """move a user from members back to guests"""
    pk = payload.get("pk")
    if pk is None:
        raise HTTPException(status_code=400, detail="pk is required")
    try:
        pk_i = int(pk)
    except Exception:
        raise HTTPException(status_code=400, detail="pk must be an integer")

    result = ak.switch_group_user_pk(
        settings.AK_MEMBERS_GROUP_UUID,
        settings.AK_GUESTS_GROUP_UUID,
        pk_i,
    )
    return {"status": "ok", **result}


@router.post("/promote/bulk")
def promote_bulk(payload: Dict[str, Any] = Body(...)):
    """promote many users in one call; duplicates are deduped, capped to a safe limit"""
    raw = payload.get("pks")
    if not isinstance(raw, list) or not raw:
        raise HTTPException(status_code=400, detail="pks must be a non-empty array")

    try:
        pks = list({int(x) for x in raw})
    except Exception:
        raise HTTPException(status_code=400, detail="all pks must be integers")

    max_items = 200
    if len(pks) > max_items:
        raise HTTPException(status_code=413, detail=f"too many pks (>{max_items})")

    send_mail = bool(payload.get("send_mail", True))

    results: list[dict[str, Any]] = []
    ok = 0
    fail = 0

    logger.info("bulk_promote_requested", extra={"count": len(pks), "send_mail": send_mail})

    for pk in pks:
        try:
            res = ak.switch_group_user_pk(
                settings.AK_GUESTS_GROUP_UUID,
                settings.AK_MEMBERS_GROUP_UUID,
                pk,
            )
            success = 200 <= res["add"] < 300 and 200 <= res["remove"] < 300
            if success and send_mail:
                # mail is best-effort per user
                try:
                    u = ak.get_user(pk)
                    to_email = (u.get("email") or "").strip()
                    name = (u.get("name") or u.get("username") or "").strip()
                    if to_email:
                        send_promotion_email(
                            to_email=to_email,
                            name=name,
                            portal_url=settings.PORTAL_URL,
                            authentik_url=settings.AK_BASE_URL,
                            org_name=settings.ORGANIZATION_NAME,
                            external_url=settings.EXTERNAL_BASE_URL,
                            footer=settings.EMAIL_FOOTER,
                        )
                except Exception as e:
                    logger.warning("bulk promotion email failed", extra={"pk": pk, "error": str(e)})

            results.append({"pk": pk, "ok": success, "detail": res})
            ok += 1 if success else 0
            fail += 0 if success else 1
            logger.debug("promote_result", extra={"pk": pk, "ok": success})
        except Exception as e:
            results.append({"pk": pk, "ok": False, "detail": str(e)})
            fail += 1
            logger.debug("promote_exception", extra={"pk": pk, "error": str(e)})

    logger.info("bulk_promote_finished", extra={"ok": ok, "failed": fail})
    return {"count_ok": ok, "count_failed": fail, "results": results}


@router.post("/demote/bulk")
def demote_bulk(payload: Dict[str, Any] = Body(...)):
    """demote many users in one call; duplicates are deduped, capped to a safe limit"""
    raw = payload.get("pks")
    if not isinstance(raw, list) or not raw:
        raise HTTPException(status_code=400, detail="pks must be a non-empty array")

    try:
        pks = list({int(x) for x in raw})
    except Exception:
        raise HTTPException(status_code=400, detail="all pks must be integers")

    max_items = 200
    if len(pks) > max_items:
        raise HTTPException(status_code=413, detail=f"too many pks (>{max_items})")

    results: list[dict[str, Any]] = []
    ok = 0
    fail = 0

    logger.info("bulk_demote_requested", extra={"count": len(pks)})

    for pk in pks:
        try:
            res = ak.switch_group_user_pk(
                settings.AK_MEMBERS_GROUP_UUID,
                settings.AK_GUESTS_GROUP_UUID,
                pk,
            )
            success = 200 <= res["add"] < 300 and 200 <= res["remove"] < 300
            results.append({"pk": pk, "ok": success, "detail": res})
            ok += 1 if success else 0
            fail += 0 if success else 1

            logger.debug("demote_result", extra={"pk": pk, "ok": success})
        except Exception as e:
            results.append({"pk": pk, "ok": False, "detail": str(e)})
            fail += 1
            logger.debug("demote_exception", extra={"pk": pk, "error": str(e)})

    logger.info("bulk_demote_finished", extra={"ok": ok, "failed": fail})
    return {"count_ok": ok, "count_failed": fail, "results": results}
