# services/brand.py
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, Optional

from fastapi import FastAPI

from tools.settings import settings
from services.authentik import ak

log = logging.getLogger("authentik_helper.brand")


def normalize_str(s: Optional[str]) -> Optional[str]:
    """return s if it is a non-empty, non-whitespace string; else None"""
    if s is None:
        return None
    v = str(s).strip()
    return v if v else None


def _build_portal_url(brand_domain: str, base_url: Optional[str]) -> Optional[str]:
    dom = normalize_str(brand_domain)
    if not dom:
        return normalize_str(base_url)
    if dom.startswith("http://") or dom.startswith("https://"):
        return dom
    return f"https://{dom}"


@lru_cache(maxsize=1)
def _fetch_brand() -> Dict[str, Any]:
    """raw brand fetch from authentik (no settings merge)"""
    brand_uuid = normalize_str(getattr(settings, "AK_BRAND_UUID", None))
    if not brand_uuid:
        log.info("brand_uuid_missing_using_settings_fallback")
        return {"name": None, "portal": None, "logo": "", "favicon": ""}

    try:
        info = ak.brand_info(brand_uuid)
        name = normalize_str(info.get("brand_name"))
        portal = _build_portal_url(info.get("brand_domain", ""), None)
        logo = info.get("brand_logo") or ""
        favicon = info.get("brand_favicon") or ""
        log.info(
            "brand_loaded",
            extra={"brand_name": name, "brand_portal": portal, "has_logo": bool(logo)},
        )
        return {"name": name, "portal": portal, "logo": logo, "favicon": favicon}
    except Exception as e:
        log.warning("brand_fetch_failed_falling_back", extra={"error": str(e)}, exc_info=True)
        return {"name": None, "portal": None, "logo": "", "favicon": ""}


def refresh_brand_defaults() -> Dict[str, Any]:
    """clear cache and refetch (call at startup or after config change)"""
    _fetch_brand.cache_clear()
    return _fetch_brand()


def brand_ctx(app: Optional[FastAPI] = None) -> Dict[str, Any]:
    """
    merged brand context where SETTINGS OVERRIDE BRAND:
      org_name   = settings.ORGANIZATION_NAME or brand.name or "authentik"
      portal_url = settings.PORTAL_URL         or brand.portal or ""
      brand_logo = settings.BRAND_LOGO         or brand.logo
      brand_favicon = settings.BRAND_FAVICON   or brand.favicon
    """
    # prefer warmed app.state if present
    state_brand: Optional[Dict[str, Any]] = None
    if app is not None:
        state = getattr(app, "state", None)
        if state is not None and hasattr(state, "brand"):
            try:
                # allow app.state.brand to be the raw brand or the merged context;
                # if it's raw, we'll still merge with settings below.
                b = getattr(state, "brand")
                if isinstance(b, dict):
                    state_brand = b
            except Exception:
                pass

    raw_brand = state_brand or _fetch_brand()

    # settings overrides (treat empty strings as "unset")
    s_name = normalize_str(getattr(settings, "ORGANIZATION_NAME", None))
    s_portal = normalize_str(getattr(settings, "PORTAL_URL", None))
    s_logo = normalize_str(getattr(settings, "BRAND_LOGO", None))

    # brand values
    b_name = normalize_str(raw_brand.get("name"))
    b_portal = normalize_str(raw_brand.get("portal"))
    b_logo = normalize_str(raw_brand.get("logo")) or normalize_str(raw_brand.get("favicon")) or ""

    # final (settings win)
    name = s_name or b_name or ""
    portal = s_portal or b_portal or ""
    logo = s_logo or b_logo

    return {
        "org_name": name,
        "portal_url": portal,
        "brand_logo": logo,
    }
