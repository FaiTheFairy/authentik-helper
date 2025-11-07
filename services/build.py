# services/build.py
from __future__ import annotations
import os, subprocess
from typing import Dict, Optional
from functools import lru_cache
from pathlib import Path
from fastapi import FastAPI

# Your canonical repo (change if you move hosts). Env can still override.
DEFAULT_REPO_URL = "https://github.com/FaiTheFairy/authentik-helper"


def _short(h: Optional[str]) -> str:
    h = (h or "").strip()
    return h[:7] if len(h) >= 7 else (h or "")


def _baked_meta() -> Dict[str, str]:
    """Load version/commit baked at build time by setuptools-scm (_version.py)."""
    try:
        from authentik_helper._version import __version__ as v, __commit__ as c  # type: ignore

        return {"version": v or "", "commit": c or ""}
    except Exception:
        return {"version": "", "commit": ""}


@lru_cache(maxsize=1)
def _computed_from_git() -> Dict[str, str]:
    """Last-resort: derive commit/repo from a live git checkout (dev only)."""
    out: Dict[str, str] = {"commit": "", "repo": ""}
    try:
        repo_root = Path(__file__).resolve().parents[1]
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(repo_root), text=True
        ).strip()
        out["commit"] = commit
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], cwd=str(repo_root), text=True
        ).strip()
        if url.startswith("git@"):
            host, path = url.split("@", 1)[1].split(":", 1)
            url = f"https://{host}/{path}"
        out["repo"] = url.removesuffix(".git").rstrip("/")
    except Exception:
        pass
    return out


def build_ctx(app: Optional[FastAPI] = None) -> Dict[str, str]:
    baked = _baked_meta()

    # baked constants from wheel/sdist (preferred)
    version = baked["version"]
    commit = baked["commit"]

    # env overrides (Docker/systemd can set these)
    version = os.getenv("BUILD_VERSION", version)
    commit = os.getenv("BUILD_COMMIT", commit) or os.getenv("GIT_COMMIT", commit)
    date = os.getenv("BUILD_DATE", "")

    # app.version as a final fallback for version
    if not version and app is not None:
        version = getattr(app, "version", "") or version

    # repository URL: env → git → default
    repo = os.getenv("REPO_URL", "")
    if not repo:
        repo = _computed_from_git().get("repo", "")
    if not repo:
        repo = DEFAULT_REPO_URL

    # commit from git if still missing (dev only)
    if not commit:
        commit = _computed_from_git().get("commit", "")

    return {
        "app_version": version or "0+unknown",
        "app_commit": commit,
        "app_commit_short": _short(commit),
        "app_build_date": date,
        "repo_url": repo.rstrip("/"),
    }
