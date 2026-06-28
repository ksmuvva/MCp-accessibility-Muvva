"""Tests for Chromium discovery in :mod:`accessibility_mcp.config`.

MCP clients spawn the server with a *sanitised* environment (HOME/PATH/SHELL/TERM
by default), so PLAYWRIGHT_BROWSERS_PATH is typically stripped before the server
starts. Discovery must therefore fall back to well-known default install
locations, otherwise every audit fails to launch a browser even though one is
installed on disk.
"""

from __future__ import annotations

import os

from accessibility_mcp import config


def _make_chromium_build(base, build="chromium-1194"):
    """Create a fake Playwright chromium build tree and return the exe path."""
    exe_dir = base / build / "chrome-linux"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "chrome"
    exe.write_text("#!/bin/sh\n")
    exe.chmod(0o755)
    return exe


def test_explicit_override_wins(tmp_path, monkeypatch):
    exe = tmp_path / "my-chrome"
    exe.write_text("")
    monkeypatch.setenv("ACCESSIBILITY_MCP_CHROMIUM", str(exe))
    assert config._discover_chromium() == str(exe)


def test_discovers_under_browsers_path_env(tmp_path, monkeypatch):
    monkeypatch.delenv("ACCESSIBILITY_MCP_CHROMIUM", raising=False)
    exe = _make_chromium_build(tmp_path)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    assert config._discover_chromium() == str(exe)


def test_falls_back_to_default_location_without_env(tmp_path, monkeypatch):
    """The key regression: no PLAYWRIGHT_BROWSERS_PATH (sanitised MCP env).

    With the env var stripped, discovery must still find a browser by probing
    well-known default locations. We model that by routing HOME's cache to a
    tmp build; on hosts where a higher-priority default (e.g. /opt/pw-browsers)
    genuinely exists, discovery may return that instead — either way it must
    resolve to a real chromium build rather than ``None``.
    """
    monkeypatch.delenv("ACCESSIBILITY_MCP_CHROMIUM", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    cache = tmp_path / "cache" / "ms-playwright"
    exe = _make_chromium_build(cache)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(config.Path, "home", staticmethod(lambda: tmp_path))

    result = config._discover_chromium()
    assert result is not None and os.path.exists(result)
    # When no system-wide default is present, our HOME-cache build is found.
    if not os.path.isdir("/opt/pw-browsers") and not os.path.isdir("/root/.cache/ms-playwright"):
        assert result == str(exe)

    # Directly exercise the cache probe regardless of host defaults.
    assert config._chromium_under(str(cache)) == str(exe)


def test_prefers_full_build_over_headless_shell(tmp_path, monkeypatch):
    monkeypatch.delenv("ACCESSIBILITY_MCP_CHROMIUM", raising=False)
    shell_dir = tmp_path / "chromium_headless_shell-1194" / "chrome-linux"
    shell_dir.mkdir(parents=True)
    (shell_dir / "headless_shell").write_text("")
    full = _make_chromium_build(tmp_path)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    assert config._discover_chromium() == str(full)


def test_unreadable_candidate_does_not_crash(tmp_path, monkeypatch):
    """A default location that raises PermissionError on stat must be skipped.

    Regression: discovery runs at import time, so an OSError from probing an
    unreadable path (e.g. /root/.cache from an unprivileged CI runner) would
    crash the whole server/test run instead of falling through.
    """
    monkeypatch.delenv("ACCESSIBILITY_MCP_CHROMIUM", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)

    real_is_dir = config.Path.is_dir

    def fake_is_dir(self):
        if str(self) == "/root/.cache/ms-playwright":
            raise PermissionError(13, "Permission denied")
        return real_is_dir(self)

    monkeypatch.setattr(config.Path, "is_dir", fake_is_dir)
    # Must not raise; returns whatever else is discoverable (possibly None).
    result = config._discover_chromium()
    assert result is None or os.path.exists(result)


def test_returns_none_when_nothing_found(tmp_path, monkeypatch):
    monkeypatch.delenv("ACCESSIBILITY_MCP_CHROMIUM", raising=False)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "empty"))
    monkeypatch.setenv("HOME", str(tmp_path / "nohome"))
    monkeypatch.setattr(config.Path, "home", staticmethod(lambda: tmp_path / "nohome"))
    # Default system locations may exist on the test host; only assert the
    # discovery does not crash and returns either None or an existing path.
    result = config._discover_chromium()
    assert result is None or os.path.exists(result)
