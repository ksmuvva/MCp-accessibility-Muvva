"""Run axe-core against a rendered page and return its raw results.

axe-core is the industry-standard accessibility engine and the only mature one
with explicit WCAG 2.2 rule tags (``wcag22aa``). It is JavaScript, so we inject the
vendored bundle into a live Chromium page (via Playwright) and invoke ``axe.run``.

This module deliberately returns axe's *raw* result structure (violations / passes /
incomplete / inapplicable). Mapping into our own report models, GOV.UK checks and
remediation guidance happens in the reporting and rules layers.
"""

from __future__ import annotations

from functools import lru_cache

from playwright.async_api import Page

from accessibility_mcp import config


@lru_cache(maxsize=1)
def _axe_source() -> str:
    """Read the vendored axe-core bundle once and cache it."""
    if not config.AXE_SCRIPT_PATH.exists():
        raise FileNotFoundError(
            f"Vendored axe-core not found at {config.AXE_SCRIPT_PATH}. "
            "Run the build step that downloads axe-core into the vendor/ directory."
        )
    return config.AXE_SCRIPT_PATH.read_text(encoding="utf-8")


async def load_page(page: Page, *, url: str | None = None, html: str | None = None) -> None:
    """Load content into the page from a URL or a raw HTML string.

    Exactly one of ``url`` or ``html`` must be provided.
    """
    if (url is None) == (html is None):
        raise ValueError("Provide exactly one of 'url' or 'html'.")
    if url is not None:
        # 'load' waits for the load event; axe needs the DOM and styles present.
        await page.goto(url, wait_until="load")
    else:
        await page.set_content(html, wait_until="load")  # type: ignore[arg-type]


async def run_axe(page: Page, tags: list[str]) -> dict:
    """Inject axe-core and run it, restricted to the given rule tags.

    Returns axe's raw result object with keys: ``violations``, ``passes``,
    ``incomplete`` (needs manual review), ``inapplicable``, plus ``testEngine`` etc.
    """
    await page.add_script_tag(content=_axe_source())

    # axe.run is promise-based; Playwright resolves the promise for us.
    results = await page.evaluate(
        """
        async (tags) => {
            return await axe.run(document, {
                runOnly: { type: 'tag', values: tags },
                resultTypes: ['violations', 'passes', 'incomplete', 'inapplicable'],
            });
        }
        """,
        tags,
    )
    return results


async def run_axe_rules(page: Page, rule_ids: list[str]) -> dict:
    """Inject axe-core and run it restricted to specific rule ids.

    Powers the per-rule MCP tools (one axe rule per tool).
    """
    await page.add_script_tag(content=_axe_source())
    results = await page.evaluate(
        """
        async (ruleIds) => {
            return await axe.run(document, {
                runOnly: { type: 'rule', values: ruleIds },
                resultTypes: ['violations', 'passes', 'incomplete', 'inapplicable'],
            });
        }
        """,
        rule_ids,
    )
    return results


def axe_engine_version() -> str:
    """Best-effort axe-core version extracted from the vendored bundle header."""
    head = _axe_source()[:80]
    # Header looks like: /*! axe v4.12.1 ...
    marker = "axe v"
    idx = head.find(marker)
    if idx != -1:
        return head[idx + len(marker) :].split()[0].strip()
    return "unknown"


async def audit(
    page: Page,
    *,
    url: str | None = None,
    html: str | None = None,
    level: str = config.DEFAULT_LEVEL,
    include_best_practice: bool = False,
) -> dict:
    """Convenience: load content and run axe with the level's WCAG tags."""
    await load_page(page, url=url, html=html)
    tags = config.axe_tags(level=level, include_best_practice=include_best_practice)
    return await run_axe(page, tags)
