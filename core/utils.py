# core/utils.py
from __future__ import annotations


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
