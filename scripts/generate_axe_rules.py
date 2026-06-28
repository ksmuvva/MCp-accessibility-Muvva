#!/usr/bin/env python
"""Generate ``accessibility_mcp/vendor/axe-rules.json`` from the vendored axe-core.

Runs axe-core in a headless Chromium and dumps ``axe.getRules()`` metadata (rule
id, description, help, helpUrl, tags) to a static JSON file. The server loads that
JSON at import time so it can register one MCP tool per axe rule *without* launching
a browser on startup.

Run after updating the vendored axe.min.js:

    python scripts/generate_axe_rules.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

from accessibility_mcp import config

OUT = config.VENDOR_DIR / "axe-rules.json"


async def main() -> None:
    axe_src = config.AXE_SCRIPT_PATH.read_text(encoding="utf-8")
    launch_kwargs: dict = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    if config.CHROMIUM_EXECUTABLE:
        launch_kwargs["executable_path"] = config.CHROMIUM_EXECUTABLE
    if config.PROXY_SERVER:
        launch_kwargs["proxy"] = {"server": config.PROXY_SERVER}

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        page = await browser.new_page()
        await page.set_content("<!doctype html><html><body></body></html>")
        await page.add_script_tag(content=axe_src)
        rules = await page.evaluate("() => axe.getRules()")
        version = await page.evaluate("() => axe.version")
        await browser.close()

    payload = {"axe_version": version, "rules": rules}
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {len(rules)} axe rules (axe {version}) -> {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
