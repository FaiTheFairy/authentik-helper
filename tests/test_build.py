# tests/test_build.py

import os
import sys
import types
import pytest

import services.build as build


def _clear_env(keys):
    for k in keys:
        os.environ.pop(k, None)


def _clear_git_cache():
    # ensure each test starts fresh for _computed_from_git()
    try:
        build._computed_from_git.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _isolate_env_and_cache():
    keep = dict(os.environ)
    _clear_git_cache()
    yield
    # restore env and clear cache again
    os.environ.clear()
    os.environ.update(keep)
    _clear_git_cache()


def test_short_hash():
    assert build._short("abcdef1") == "abcdef1"
    assert build._short("abcdef123456") == "abcdef1"
    assert build._short("") == ""
    assert build._short(None) == ""


def test_baked_metadata_preferred(monkeypatch):
    # Provide authentik_helper._version with baked values
    baked = types.ModuleType("authentik_helper._version")
    baked.__version__ = "1.2.3"
    baked.__commit__ = "abcdef1234567890"
    sys.modules["authentik_helper._version"] = baked

    _clear_env(["BUILD_VERSION", "BUILD_COMMIT", "GIT_COMMIT", "BUILD_DATE", "REPO_URL"])
    _clear_git_cache()

    ctx = build.build_ctx(app=None)

    assert ctx["app_version"] == "1.2.3"
    assert ctx["app_commit"] == "abcdef1234567890"
    assert ctx["app_commit_short"] == "abcdef1"
    # default repo URL should be used when REPO_URL not set and no git info needed
    assert ctx["repo_url"] == build.DEFAULT_REPO_URL.rstrip("/")
    # BUILD_DATE not set
    assert ctx["app_build_date"] == ""


def test_env_overrides(monkeypatch):
    # Remove baked module to ensure env wins
    sys.modules.pop("authentik_helper._version", None)

    os.environ["BUILD_VERSION"] = "9.9.9"
    os.environ["BUILD_COMMIT"] = "deadbeefcafebabe"
    os.environ["BUILD_DATE"] = "2025-10-29T12:34:56Z"
    os.environ["REPO_URL"] = "https://git.example.com/acme/thing"

    ctx = build.build_ctx()

    assert ctx["app_version"] == "9.9.9"
    assert ctx["app_commit"] == "deadbeefcafebabe"
    assert ctx["app_commit_short"] == "deadbee"
    assert ctx["app_build_date"] == "2025-10-29T12:34:56Z"
    assert ctx["repo_url"] == "https://git.example.com/acme/thing"


def test_app_version_fallback_when_no_baked_or_env(monkeypatch):
    # No baked metadata
    sys.modules.pop("authentik_helper._version", None)
    _clear_env(["BUILD_VERSION", "BUILD_COMMIT", "GIT_COMMIT", "BUILD_DATE", "REPO_URL"])

    # Mock git fallbacks for commit only
    def fake_check_output(args, cwd=None, text=None):
        if args[:3] == ["git", "rev-parse", "--short"]:
            return "1234abc\n"
        if args[:3] == ["git", "remote", "get-url"]:
            # Let repo fallback stay at DEFAULT_REPO_URL by returning an error via exception;
            # here we just simulate no remote by raising.
            raise RuntimeError("no remote")
        raise AssertionError(f"unexpected git call: {args}")

    monkeypatch.setattr(build.subprocess, "check_output", fake_check_output)
    _clear_git_cache()

    app = types.SimpleNamespace(version="2.0.0")
    ctx = build.build_ctx(app=app)

    assert ctx["app_version"] == "2.0.0"
    # commit pulled from git fallback
    assert ctx["app_commit"] == "1234abc"
    assert ctx["app_commit_short"] == "1234abc"
    # repo falls back to DEFAULT_REPO_URL
    assert ctx["repo_url"] == build.DEFAULT_REPO_URL.rstrip("/")


def test_git_remote_ssh_converted_to_https_and_stripped(monkeypatch):
    # No baked/env
    sys.modules.pop("authentik_helper._version", None)
    _clear_env(["BUILD_VERSION", "BUILD_COMMIT", "GIT_COMMIT", "BUILD_DATE", "REPO_URL"])

    calls = {"revparse": 0, "remote": 0}

    def fake_check_output(args, cwd=None, text=None):
        if args[:3] == ["git", "rev-parse", "--short"]:
            calls["revparse"] += 1
            return "beef123\n"
        if args[:3] == ["git", "remote", "get-url"]:
            calls["remote"] += 1
            # SSH-like remote
            return "git@github.com:FaiTheFairy/authentik-helper.git\n"
        raise AssertionError(f"unexpected git call: {args}")

    monkeypatch.setattr(build.subprocess, "check_output", fake_check_output)
    _clear_git_cache()

    ctx = build.build_ctx()

    assert ctx["app_commit"] == "beef123"
    assert ctx["app_commit_short"] == "beef123"
    # Should normalize SSH to HTTPS and strip .git
    assert ctx["repo_url"] == "https://github.com/FaiTheFairy/authentik-helper"
    assert calls["revparse"] == 1
    assert calls["remote"] == 1


def test_git_https_remote_kept_and_trimmed(monkeypatch):
    sys.modules.pop("authentik_helper._version", None)
    _clear_env(["BUILD_VERSION", "BUILD_COMMIT", "GIT_COMMIT", "BUILD_DATE", "REPO_URL"])

    def fake_check_output(args, cwd=None, text=None):
        if args[:3] == ["git", "rev-parse", "--short"]:
            return "aa11bb2\n"
        if args[:3] == ["git", "remote", "get-url"]:
            return "https://git.example.org/acme/repo.git\n"
        raise AssertionError(f"unexpected git call: {args}")

    monkeypatch.setattr(build.subprocess, "check_output", fake_check_output)
    _clear_git_cache()

    ctx = build.build_ctx()

    assert ctx["app_commit"] == "aa11bb2"
    assert ctx["repo_url"] == "https://git.example.org/acme/repo"


def test_env_commit_overrides_baked_and_git(monkeypatch):
    # Provide baked, but env should override commit
    baked = types.ModuleType("authentik_helper._version")
    baked.__version__ = "1.0.0"
    baked.__commit__ = "aaaaaaaaaaaaaaa"
    sys.modules["authentik_helper._version"] = baked

    os.environ["BUILD_COMMIT"] = "zzzzzz1"
    _clear_git_cache()

    ctx = build.build_ctx()

    assert ctx["app_version"] == "1.0.0"  # from baked
    assert ctx["app_commit"] == "zzzzzz1"  # env override
    assert ctx["app_commit_short"] == "zzzzzz1"  # already short
    assert ctx["repo_url"] == build.DEFAULT_REPO_URL.rstrip("/")
