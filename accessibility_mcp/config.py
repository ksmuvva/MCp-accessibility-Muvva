"""Configuration for the accessibility MCP server.

Central place for WCAG tag selection, browser discovery, timeouts and crawl limits.
All values can be overridden with environment variables so the server adapts to
different deployments (local dev, CI, the managed remote execution environment).
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# axe-core / WCAG tag selection
# --------------------------------------------------------------------------- #

# Vendored axe-core bundle (no CDN dependency — works offline / in CI).
VENDOR_DIR = Path(__file__).parent / "vendor"
AXE_SCRIPT_PATH = VENDOR_DIR / "axe.min.js"

# axe-core rule tags grouped by WCAG conformance level. Public sector bodies must
# meet WCAG 2.2 AA, which is cumulative: it includes everything from 2.0 and 2.1.
WCAG_TAGS_BY_LEVEL: dict[str, list[str]] = {
    "A": ["wcag2a", "wcag21a", "wcag22a"],
    "AA": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
    "AAA": [
        "wcag2a",
        "wcag2aa",
        "wcag2aaa",
        "wcag21a",
        "wcag21aa",
        "wcag22a",
        "wcag22aa",
    ],
}

# The GOV.UK / GDS default: WCAG 2.2 level AA.
DEFAULT_LEVEL = "AA"

# axe "best-practice" rules are not WCAG requirements but catch common usability
# and a11y problems GDS reviewers flag. Opt-in per call.
BEST_PRACTICE_TAG = "best-practice"


def axe_tags(level: str = DEFAULT_LEVEL, include_best_practice: bool = False) -> list[str]:
    """Return the axe-core tag list for a conformance level."""
    tags = list(WCAG_TAGS_BY_LEVEL.get(level.upper(), WCAG_TAGS_BY_LEVEL[DEFAULT_LEVEL]))
    if include_best_practice:
        tags.append(BEST_PRACTICE_TAG)
    return tags


# --------------------------------------------------------------------------- #
# Browser discovery
# --------------------------------------------------------------------------- #


def _discover_chromium() -> str | None:
    """Locate a Chromium executable.

    Order of precedence:
      1. ACCESSIBILITY_MCP_CHROMIUM env var (explicit override).
      2. A chromium build under PLAYWRIGHT_BROWSERS_PATH (the managed remote
         environment pre-installs Chromium there but the pinned playwright pip
         version may differ, so we point at the binary directly).
      3. None -> let Playwright resolve its own managed browser.
    """
    override = os.environ.get("ACCESSIBILITY_MCP_CHROMIUM")
    if override and Path(override).exists():
        return override

    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if browsers_path and Path(browsers_path).is_dir():
        # Prefer the full chromium build; fall back to the headless shell.
        patterns = [
            os.path.join(browsers_path, "chromium-*", "chrome-linux", "chrome"),
            os.path.join(browsers_path, "chromium_headless_shell-*", "chrome-linux", "headless_shell"),
            os.path.join(browsers_path, "chromium-*", "chrome-mac", "Chromium.app", "Contents", "MacOS", "Chromium"),
        ]
        for pattern in patterns:
            matches = sorted(glob.glob(pattern))
            if matches:
                return matches[-1]  # highest build number
    return None


CHROMIUM_EXECUTABLE: str | None = _discover_chromium()


# --------------------------------------------------------------------------- #
# Timeouts and limits (all overridable via env)
# --------------------------------------------------------------------------- #


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# Page navigation / load timeout in milliseconds.
PAGE_TIMEOUT_MS = _int_env("ACCESSIBILITY_MCP_PAGE_TIMEOUT_MS", 30_000)

# Crawl limits (audit_site).
DEFAULT_MAX_PAGES = _int_env("ACCESSIBILITY_MCP_MAX_PAGES", 20)
MAX_PAGES_CEILING = _int_env("ACCESSIBILITY_MCP_MAX_PAGES_CEILING", 100)
DEFAULT_MAX_DEPTH = _int_env("ACCESSIBILITY_MCP_MAX_DEPTH", 2)
MAX_DEPTH_CEILING = _int_env("ACCESSIBILITY_MCP_MAX_DEPTH_CEILING", 5)

# A descriptive UA so site owners can identify the auditor in their logs.
USER_AGENT = os.environ.get(
    "ACCESSIBILITY_MCP_USER_AGENT",
    "AccessibilityMCP/0.1 (+WCAG2.2-AA auditor; GOV.UK standard)",
)


# --------------------------------------------------------------------------- #
# Outbound proxy
# --------------------------------------------------------------------------- #


def _discover_proxy() -> str | None:
    """Resolve an outbound HTTP(S) proxy for the browser from the environment.

    Honours ACCESSIBILITY_MCP_PROXY first, then the conventional HTTPS_PROXY /
    https_proxy / HTTP_PROXY variables. Chromium does not read these automatically,
    so the browser layer passes the result to Playwright explicitly. Returns None
    when no proxy is configured (direct connection).
    """
    for var in ("ACCESSIBILITY_MCP_PROXY", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        value = os.environ.get(var)
        if value:
            return value
    return None


PROXY_SERVER: str | None = _discover_proxy()

# Hosts that must bypass the proxy (Playwright wants a comma-separated list).
PROXY_BYPASS: str = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
