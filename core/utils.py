# core/utils.py
from __future__ import annotations

import re
import unicodedata
import uuid


def redact_email(addr: str | None) -> str:
    """return a lightly redacted email for logs and ui"""
    if not addr:
        return "-"
    try:
        local, domain = addr.split("@", 1)
        return f"{local[:2]}***@{domain}"
    except Exception:
        # don't leak anything if the input is malformed
        return "***"


def slugify_name(s: str | None) -> str:
    """Return a slug suitable for Authentik resource names.

    Keeps only lower-case letters, digits and hyphens. Returns empty string
    when nothing sensible remains (caller may fallback to a uuid-based name).
    """
    text = (s or "").strip()
    if not text:
        return ""
    # normalize accents, remove non-ascii
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    # remove characters except letters, digits, spaces and hyphen
    text = re.sub(r'[^a-z0-9\s-]', "", text)
    # spaces/underscores -> hyphen
    text = re.sub(r'[\s_]+', "-", text)
    # collapse multiple hyphens
    text = re.sub(r'-{2,}', "-", text)
    text = text.strip('-')
    return text
