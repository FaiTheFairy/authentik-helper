# tools/logging_config.py
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, Literal, Optional

LevelName = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


# formatters
class JSONFormatter(logging.Formatter):
    """compact ndjson formatter with a strict allowlist of extra fields"""

    _allowed_extra: set[str] = {
        # request/response
        "method",
        "path",
        "status",
        "duration_ms",
        "request_id",
        # startup/config
        "external_origin",
        "issuer",
        "disable_auth",
        "allow_origins",
        # auth/user
        "sub",
        "email",
        "scopes",
        # ops/search/bulk
        "q",
        "results",
        "count",
        "send_mail",
        "ok",
        "failed",
        "pk",
        "result",
        # invites/emails
        "end_session",
        "post_logout",
        # email transport
        "host",
        "port",
        "from",
        "to",
        "auth",
        "missing",
        # invite creation diagnostics
        "has_flow",
        "name_set",
        "email_set",
        # generic error
        "error",
    }

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        data: Dict[str, Any] = {
            "ts": ts,
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for key in self._allowed_extra:
            if hasattr(record, key):
                data[key] = getattr(record, key)
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


class HumanFormatter(logging.Formatter):
    """readable, single-line console logs"""

    def __init__(self) -> None:
        super().__init__(
            "%(asctime)s %(levelname)s %(name)s [rid=%(request_id)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


# request id filter
class RequestIdFilter(logging.Filter):
    """inject request_id from a callable so every record carries it"""

    def __init__(self, request_id_ctx_getter: Callable[[], Optional[str]]) -> None:
        super().__init__()
        self._get = request_id_ctx_getter

    def filter(self, record: logging.LogRecord) -> bool:
        rid = self._get() or "-"
        setattr(record, "request_id", rid)
        return True


# setup
def _ensure_parent(path: Path) -> None:
    """create parent directories if missing"""
    path.parent.mkdir(parents=True, exist_ok=True)


def setup_logging(
    get_request_id: Callable[[], Optional[str]],
    *,
    level: LevelName | str = "INFO",
    # file logging
    file_path: Optional[str] = None,
    file_rotate: Literal["size", "time"] = "size",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    when: str = "midnight",  # for time rotation
    interval: int = 1,  # for time rotation
) -> None:
    """
    configure logging:
      - stdout: human-readable single-line logs
      - file (optional): rotating ndjson logs for ingestion
      - uvicorn: WARNING+ only, propagate through our handlers
    """
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, str(level), logging.INFO))

    rid_filter = RequestIdFilter(get_request_id)

    # console (stdout)
    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(HumanFormatter())
    console.addFilter(rid_filter)
    root.addHandler(console)

    # rotating json file
    if file_path:
        p = Path(file_path)
        _ensure_parent(p)
        if file_rotate == "time":
            fh: logging.Handler = TimedRotatingFileHandler(
                filename=str(p),
                when=when,
                interval=interval,
                backupCount=backup_count,
                encoding="utf-8",
                utc=True,
            )
        else:
            fh = RotatingFileHandler(
                filename=str(p),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
                delay=True,
            )
        fh.setFormatter(JSONFormatter())
        fh.addFilter(rid_filter)
        root.addHandler(fh)

    # quiet uvicorn info; keep warnings/errors
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
        lg.setLevel(logging.WARNING)
