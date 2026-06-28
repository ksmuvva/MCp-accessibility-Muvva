"""Headless Chromium lifecycle management via Playwright (async API).

A single ``BrowserSession`` owns one Playwright instance and one Chromium browser,
reused across many page audits to amortise startup cost. Pages are created and
disposed per audit. The session resolves the Chromium executable from
:mod:`accessibility_mcp.config` so it works against the pre-installed browser in the
managed remote environment without a ``playwright install`` download.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from types import TracebackType

from playwright.async_api import Browser, Page, Playwright, async_playwright

from accessibility_mcp import config


class BrowserSession:
    """Manages a reusable headless Chromium instance."""

    def __init__(self, executable_path: str | None = None) -> None:
        # Fall back to config discovery; None lets Playwright use its own browser.
        self._executable_path = executable_path or config.CHROMIUM_EXECUTABLE
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        if self._browser is not None:
            return
        self._playwright = await async_playwright().start()
        launch_kwargs: dict[str, object] = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"],
        }
        if self._executable_path:
            launch_kwargs["executable_path"] = self._executable_path
        # Chromium does not read HTTPS_PROXY from the environment; pass it through
        # explicitly so audits work behind an egress proxy (e.g. the managed env).
        if config.PROXY_SERVER:
            proxy: dict[str, str] = {"server": config.PROXY_SERVER}
            if config.PROXY_BYPASS:
                # Playwright expects comma-separated hosts; CIDR entries are ignored.
                proxy["bypass"] = config.PROXY_BYPASS
            launch_kwargs["proxy"] = proxy
        self._browser = await self._playwright.chromium.launch(**launch_kwargs)

    async def close(self) -> None:
        if self._browser is not None:
            with contextlib.suppress(Exception):
                await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            with contextlib.suppress(Exception):
                await self._playwright.stop()
            self._playwright = None

    @contextlib.asynccontextmanager
    async def new_page(self) -> AsyncIterator[Page]:
        """Yield a fresh page with a descriptive user agent, disposed on exit."""
        if self._browser is None:
            await self.start()
        assert self._browser is not None
        context = await self._browser.new_context(user_agent=config.USER_AGENT)
        page = await context.new_page()
        page.set_default_timeout(config.PAGE_TIMEOUT_MS)
        try:
            yield page
        finally:
            with contextlib.suppress(Exception):
                await context.close()

    async def __aenter__(self) -> "BrowserSession":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()
