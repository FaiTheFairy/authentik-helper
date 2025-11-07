# demo/mockup.py
from __future__ import annotations
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


# repo root (demo/ lives at repo_root/demo/)
HERE = Path(__file__).resolve().parents[1]


def _wait_http(url: str, timeout: float = 12.0) -> None:
    """Wait until GET url returns 200 or timeout."""
    start = time.time()
    last_exc = None
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except Exception as e:  # noqa: BLE001
            last_exc = e
        time.sleep(0.2)
    raise RuntimeError(f"Timeout waiting for {url} (last={last_exc!r})")


def _get_json(url: str, timeout: float = 5.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _graceful_stop(p: subprocess.Popen, sig=signal.SIGTERM, wait: float = 6.0) -> None:
    """Try SIGTERM, wait a bit, then kill."""
    if p.poll() is not None:
        return
    try:
        p.send_signal(sig)
        deadline = time.time() + wait
        while time.time() < deadline:
            if p.poll() is not None:
                return
            time.sleep(0.1)
        p.kill()
    except Exception:
        pass


def main() -> int:
    repo = str(HERE)

    # pick ports that aren't busy (prefer 8001/8000)
    mock_port = 8001
    app_port = 8000

    # baseline env for the helper (child processes inherit this)
    os.environ.setdefault("DISABLE_AUTH", "true")
    os.environ["AK_BASE_URL"] = f"http://127.0.0.1:{mock_port}"

    # launch mock via uvicorn (use --app-dir so 'demo.mock_authentik' imports)
    mock_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "--app-dir",
        repo,
        "demo.mock_authentik:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(mock_port),
        "--no-server-header",
        "--log-level",
        "info",
    ]
    mock = subprocess.Popen(mock_cmd, cwd=repo, env=os.environ.copy())

    try:
        # wait until mock is up, then fetch UUIDs
        _wait_http(f"http://127.0.0.1:{mock_port}/healthz", timeout=20.0)
        uuids = _get_json(f"http://127.0.0.1:{mock_port}/demo/_group-uuids")
        guests = uuids.get("guests_uuid")
        members = uuids.get("members_uuid")
        if not guests or not members:
            raise RuntimeError("mock did not return group UUIDs")

        # share them with the helper
        os.environ["AK_GUESTS_GROUP_UUID"] = guests
        os.environ["AK_MEMBERS_GROUP_UUID"] = members

        print(
            f"Mock running on http://127.0.0.1:{mock_port}  "
            f"(guests={guests}  members={members})"
        )

        # start authentik-helper; adjust args if CLI differs
        app_cmd = ["authentik-helper", "--host", "0.0.0.0", "--port", str(app_port)]
        app = subprocess.Popen(app_cmd, cwd=repo, env=os.environ.copy())

        print(f"Helper running on http://127.0.0.1:{app_port}")
        print("Press Ctrl+C to stop both.")

        # wait for either to exit
        while True:
            if mock.poll() is not None:
                _graceful_stop(app)
                return mock.returncode
            if app.poll() is not None:
                _graceful_stop(mock)
                return app.returncode
            time.sleep(0.2)

    except KeyboardInterrupt:
        _graceful_stop(app)
        _graceful_stop(mock)
        return 0
    except Exception as e:
        print(f"[mockup] error: {e}", file=sys.stderr)
        _graceful_stop(app)
        _graceful_stop(mock)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
