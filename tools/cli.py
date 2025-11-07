#!/usr/bin/env python3
# tools/cli.py  CLI wrapper
# Pretty tables by default; --json for raw output.
# Sends emails on "invites create" (if email provided) and, optionally, "membership promote" (if user has email).

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Iterable, Mapping, Sequence

from tools import mailer


def _settings():
    from tools.settings import settings  # type: ignore

    return settings


def _ak():
    from services import authentik as svc  # type: ignore

    if not hasattr(svc, "ak"):
        _die("services.authentik must expose a pre-initialized client `ak`.")
    return svc.ak


# output helpers
def _out_json(data: Any) -> None:
    sys.stdout.write(json.dumps(data, indent=2) + "\n")


def _print_table(
    rows: Sequence[Sequence[Any]] | Sequence[Mapping[str, Any]],
    headers: Sequence[str] | None = None,
) -> None:
    if headers is None:
        if rows and isinstance(rows[0], Mapping):
            headers = list(rows[0].keys())  # type: ignore[index]
            norm_rows: list[list[str]] = [[_cell(r.get(h)) for h in headers] for r in rows]  # type: ignore[union-attr]
        else:
            headers = []
            norm_rows = [[_cell(c) for c in row] for row in rows]  # type: ignore[assignment]
    else:
        if rows and isinstance(rows[0], Mapping):
            norm_rows = [[_cell(r.get(h)) for h in headers] for r in rows]  # type: ignore[index]
        else:
            norm_rows = [[_cell(c) for c in row] for row in rows]  # type: ignore[assignment]

    if not headers:
        headers = [f"col{idx+1}" for idx in range(len(norm_rows[0]) if norm_rows else 0)]

    cols = len(headers)
    term_w = shutil.get_terminal_size((100, 20)).columns
    max_col_w = max(10, min(60, (term_w - 3 * cols - 1) // max(1, cols)))

    widths = [len(h) for h in headers]
    for row in norm_rows:
        for i in range(cols):
            val = row[i] if i < len(row) else ""
            widths[i] = max(widths[i], len(val))
    widths = [min(w, max_col_w) for w in widths]

    def border(sep: str = "-") -> str:
        return "+" + "+".join(sep * (w + 2) for w in widths) + "+"

    def fmt_row(vals: Sequence[str]) -> str:
        clipped = [(_clip(vals[i], widths[i])) for i in range(cols)]
        return "| " + " | ".join(f"{clipped[i]:{widths[i]}}" for i in range(cols)) + " |"

    print(border("-"))
    print(fmt_row([str(h) for h in headers]))
    print(border("="))
    for r in norm_rows:
        print(fmt_row(r))
    print(border("-"))


def _clip(s: str, w: int) -> str:
    return s if len(s) <= w else (s[: max(0, w - 1)] + "…")


def _cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (int, float, bool)):
        return str(v)
    return str(v)


def _maybe_page(num_rows: int) -> bool:
    if not sys.stdout.isatty() or num_rows < 30:
        return False

    less = shutil.which("less")
    if not less:
        return False
    try:
        p = subprocess.Popen([less, "-R"], stdin=subprocess.PIPE)
        sys.stdout = p.stdin if p.stdin else sys.stdout  # type: ignore[assignment]
        return True
    except Exception:
        return False


def _die(msg: str, code: int = 2) -> None:
    sys.stderr.write(msg.rstrip() + "\n")
    raise SystemExit(code)


# commands
def cmd_settings(args: argparse.Namespace) -> None:
    s = _settings()
    out = {
        "AK_BASE_URL": str(getattr(s, "AK_BASE_URL", "")),
        "EXTERNAL_BASE_URL": str(getattr(s, "EXTERNAL_BASE_URL", "")),
        "AK_GUESTS_GROUP_UUID": getattr(s, "AK_GUESTS_GROUP_UUID", None),
        "AK_MEMBERS_GROUP_UUID": getattr(s, "AK_MEMBERS_GROUP_UUID", None),
        "AK_BRAND_UUID": getattr(s, "AK_BRAND_UUID", None),
        "AK_INVITE_FLOW_SLUG": getattr(s, "AK_INVITE_FLOW_SLUG", None),
        "AK_INVITE_EXPIRES_DAYS": getattr(s, "AK_INVITE_EXPIRES_DAYS", None),
    }
    if args.json:
        _out_json(out)
        return
    _print_table(
        [[k, v if v is not None else ""] for k, v in out.items()], headers=["Setting", "Value"]
    )


def cmd_users_get(args: argparse.Namespace) -> None:
    ak = _ak()
    if not hasattr(ak, "get_user"):
        _die("Client missing method: get_user(pk)")
    data = ak.get_user(int(args.pk))  # type: ignore[attr-defined]
    if args.json:
        _out_json(data)
        return
    keys = ["pk", "username", "name", "email", "is_active", "last_login"]
    rows = [[k, data.get(k, "")] for k in keys]
    _print_table(rows, headers=["Field", "Value"])


def cmd_groups_guests(args: argparse.Namespace) -> None:
    s, ak = _settings(), _ak()
    if not hasattr(ak, "list_group_users"):
        _die("Client missing method: list_group_users(group_uuid)")
    data = ak.list_group_users(s.AK_GUESTS_GROUP_UUID)  # type: ignore[attr-defined]
    _render_group_listing(data, args)


def cmd_groups_members(args: argparse.Namespace) -> None:
    s, ak = _settings(), _ak()
    if not hasattr(ak, "list_group_users"):
        _die("Client missing method: list_group_users(group_uuid)")
    data = ak.list_group_users(s.AK_MEMBERS_GROUP_UUID)  # type: ignore[attr-defined]
    _render_group_listing(data, args)


def _render_group_listing(data: Any, args: argparse.Namespace) -> None:
    if args.json:
        _out_json(data)
        return
    if isinstance(data, dict):
        users = data.get("users") or data.get("results") or []
    else:
        users = list(data) if isinstance(data, Iterable) else []
    rows = []
    for u in users:
        rows.append(
            [
                u.get("pk", ""),
                u.get("username", ""),
                u.get("name", ""),
                u.get("email", ""),
                u.get("is_active", ""),
            ]
        )
    _maybe_page(len(rows))
    _print_table(rows, headers=["pk", "username", "name", "email", "active"])


def cmd_membership_promote(args: argparse.Namespace) -> None:
    s, ak = _settings(), _ak()
    if not hasattr(ak, "switch_group_user_pk"):
        _die("Client missing method: switch_group_user_pk(source_uuid, target_uuid, pk)")
    res = ak.switch_group_user_pk(s.AK_GUESTS_GROUP_UUID, s.AK_MEMBERS_GROUP_UUID, int(args.pk))  # type: ignore[attr-defined]
    if not args.no_email:
        try:
            u = ak.get_user(int(args.pk))  # type: ignore[attr-defined]
            to_email = (u.get("email") or "").strip()
            name = (u.get("name") or u.get("username") or "").strip()
            if to_email:
                mailer.send_promotion_email(
                    to_email=to_email,
                    name=name,
                    portal_url=_settings().PORTAL_URL,
                    authentik_url=_settings().AK_BASE_URL,
                    org_name=_settings().ORGANIZATION_NAME,
                    external_url=_settings().EXTERNAL_BASE_URL,
                    footer=_settings().EMAIL_FOOTER,
                )
        except Exception as e:
            sys.stderr.write(f"[warn] promotion email send failed: {e}\n")
    if args.json:
        _out_json({"action": "promote", "user_pk": int(args.pk), "result": res})
        return
    rows = [["action", "promote"], ["user_pk", int(args.pk)]]
    if isinstance(res, dict):
        rows += [[k, v] for k, v in res.items()]
    _print_table(rows, headers=["Field", "Value"])


def cmd_membership_demote(args: argparse.Namespace) -> None:
    s, ak = _settings(), _ak()
    if not hasattr(ak, "switch_group_user_pk"):
        _die("Client missing method: switch_group_user_pk(source_uuid, target_uuid, pk)")
    res = ak.switch_group_user_pk(s.AK_MEMBERS_GROUP_UUID, s.AK_GUESTS_GROUP_UUID, int(args.pk))  # type: ignore[attr-defined]
    if args.json:
        _out_json({"action": "demote", "user_pk": int(args.pk), "result": res})
        return
    rows = [["action", "demote"], ["user_pk", int(args.pk)]]
    if isinstance(res, dict):
        rows += [[k, v] for k, v in res.items()]
    _print_table(rows, headers=["Field", "Value"])


def cmd_invites_create(args: argparse.Namespace) -> None:
    ak = _ak()
    if not hasattr(ak, "create_invitation"):
        _die("Client missing method: create_invitation(**kwargs)")

    # create the invite in Authentik (API doesn't store/return email)
    payload: dict[str, Any] = {}
    if args.name:
        payload["name"] = args.name
    inv = ak.create_invitation(**payload)  # type: ignore[attr-defined]

    # send email if provided (same logic as web routes)
    try:
        if getattr(args, "email", None):
            mailer.send_invitation_email(
                to_email=args.email,
                name=args.name,
                invite_url=inv.get("invite_url") or inv.get("url") or "",
                expires_friendly=inv.get("expires_friendly", ""),
                org_name=_settings().ORGANIZATION_NAME,
                external_url=_settings().EXTERNAL_BASE_URL,
                footer=_settings().EMAIL_FOOTER,
            )
            sys.stderr.write(f"[info] invitation email sent to {args.email}\n")
    except Exception as e:
        sys.stderr.write(f"[warn] failed to send invitation email: {e}\n")

    # show table (PRINT THE ARG, not the API field)
    rows = [
        ["token", inv.get("pk", "") or inv.get("token", "")],
        ["name", inv.get("name", "") or (args.name or "")],
        ["email", args.email or ""],
        ["created", inv.get("created", "")],
        ["expires", inv.get("expires", "") or inv.get("expires_in", "")],
        ["flow", inv.get("flow", "")],
        ["brand", inv.get("brand", "")],
        ["url", inv.get("invite_url", "") or inv.get("url", "")],
    ]
    _print_table(rows, headers=["Field", "Value"])


def cmd_brand_info(args: argparse.Namespace) -> None:
    s, ak = _settings(), _ak()
    if not hasattr(ak, "brand_info"):
        _die("Client missing method: brand_info(brand_uuid)")
    brand_uuid = getattr(s, "AK_BRAND_UUID", None)
    if not brand_uuid:
        _die("AK_BRAND_UUID is not set in settings.")
    data = ak.brand_info(brand_uuid)  # type: ignore[attr-defined]
    if args.json:
        _out_json(data)
        return
    name = data.get("brand_name") or data.get("name") or ""
    domain = data.get("brand_domain") or data.get("domain") or ""
    logo = data.get("brand_logo") or data.get("branding_logo") or ""
    rows = [["name", name], ["domain", domain], ["logo", logo]]
    _print_table(rows, headers=["Field", "Value"])


def cmd_serve(args: argparse.Namespace) -> None:
    """Run the web app with Uvicorn (for systemd or dev)."""
    # Import here to avoid slowing down non-serve commands
    import uvicorn

    # Resolve target
    env_asgi = os.getenv("ASGI")
    target = args.asgi or env_asgi or ("web.app_factory:create_app" if args.factory else "app:app")
    factory = target.endswith(":create_app") or args.factory

    host = args.host or os.getenv("HOST", "127.0.0.1")
    port = int(args.port or os.getenv("PORT", "8088"))
    log_level = args.log_level or os.getenv("LOG_LEVEL", "info").lower()

    uvicorn.run(
        target,
        factory=factory,
        host=host,
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*",
        reload=bool(args.reload),
        log_level=log_level,
    )


# argparse wiring
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="authentik-helper", description="Authentik Helper CLI (clean tables)"
    )
    p.add_argument("--json", action="store_true", help="Output raw JSON instead of tables")

    sub = p.add_subparsers(dest="cmd", required=True)

    # serve
    psrv = sub.add_parser("serve", help="Run the web app with Uvicorn")
    psrv.add_argument("--host", help="Bind host (default: 127.0.0.1)")
    psrv.add_argument("--port", help="Bind port (default: 8088)")
    psrv.add_argument(
        "--factory",
        action="store_true",
        help="Use ASGI factory (web.app_factory:create_app)",
    )
    psrv.add_argument(
        "--asgi",
        help="Explicit ASGI target, e.g. 'app:app' or 'web.app_factory:create_app'",
    )
    psrv.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (dev only)",
    )
    psrv.add_argument(
        "--log-level",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Uvicorn log level (default: info)",
    )
    psrv.set_defaults(func=cmd_serve)

    # settings
    ps = sub.add_parser("settings", help="Show essential settings")
    ps.set_defaults(func=cmd_settings)

    # users
    pu = sub.add_parser("users", help="User operations")
    su = pu.add_subparsers(dest="subcmd", required=True)
    pug = su.add_parser("get", help="Get a user by primary key")
    pug.add_argument("pk", type=int)
    pug.set_defaults(func=cmd_users_get)

    # groups
    pg = sub.add_parser("groups", help="Group listings")
    sg = pg.add_subparsers(dest="subcmd", required=True)
    pgg = sg.add_parser("guests", help="List users in Guests")
    pgg.set_defaults(func=cmd_groups_guests)
    pgm = sg.add_parser("members", help="List users in Members")
    pgm.set_defaults(func=cmd_groups_members)

    # membership
    pm = sub.add_parser("membership", help="Promote/demote between Guests and Members")
    sm = pm.add_subparsers(dest="subcmd", required=True)
    pmp = sm.add_parser("promote", help="Guests → Members (also sends promotion email)")
    pmp.add_argument("pk", type=int)
    pmp.add_argument(
        "--no-email", action="store_true", help="Promote user without sending promotion email"
    )
    pmp.set_defaults(func=cmd_membership_promote)
    pmd = sm.add_parser("demote", help="Members → Guests")
    pmd.add_argument("pk", type=int)
    pmd.set_defaults(func=cmd_membership_demote)

    # invites
    pi = sub.add_parser("invites", help="Invitations")
    si = pi.add_subparsers(dest="subcmd", required=True)
    pic = si.add_parser("create", help="Create an invitation (sends email if --email is provided)")
    pic.add_argument("--email", help="Optional invite email")
    pic.add_argument("--name", help="Optional display name")
    pic.set_defaults(func=cmd_invites_create)

    # brand
    pb = sub.add_parser("brand", help="Brand info")
    sb = pb.add_subparsers(dest="subcmd", required=True)
    pbi = sb.add_parser("info", help="Show brand info (uses AK_BRAND_UUID)")
    pbi.set_defaults(func=cmd_brand_info)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    setattr(args, "json", getattr(args, "json", False))
    args.func(args)


if __name__ == "__main__":
    main()
