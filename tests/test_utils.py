# tests/test_utils.py
from core.utils import redact_email


def test_redact_email_ok():
    assert redact_email("alice@example.com") == "al***@example.com"


def test_redact_email_weird_inputs():
    assert redact_email(None) == "-"
    assert redact_email("") == "-"
    # no '@' -> fallback mask
    assert redact_email("notanemail") == "***"
