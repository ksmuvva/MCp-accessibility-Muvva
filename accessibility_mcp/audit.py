"""High-level audit orchestration.

Ties together the browser engine, axe-core, the GOV.UK custom checks and the
report builder. The MCP server (and tests) call these functions; they return
fully-built :class:`PageAudit` / :class:`SiteAudit` models. Errors are captured
into the model's ``error`` field rather than raised, so a single bad page never
breaks a crawl or the MCP session.
"""

from __future__ import annotations

from accessibility_mcp import config
from accessibility_mcp.engine import axe_runner
from accessibility_mcp.engine.browser import BrowserSession
from accessibility_mcp.engine.crawler import CrawlPlan, extract_links
from accessibility_mcp.reporting import builder
from accessibility_mcp.reporting.models import PageAudit, SiteAudit
from accessibility_mcp.rules import govuk_checks


async def _audit_loaded_page(page, *, target: str, level: str, include_best_practice: bool) -> PageAudit:
    """Run axe + GOV.UK checks on an already-navigated page and build the audit."""
    tags = config.axe_tags(level=level, include_best_practice=include_best_practice)
    axe_results = await axe_runner.run_axe(page, tags)
    html = await page.content()
    govuk_findings = govuk_checks.run_govuk_checks(html)
    return builder.build_page_audit(
        target=target,
        level=level,
        axe_results=axe_results,
        govuk_findings=govuk_findings,
        axe_version=axe_runner.axe_engine_version(),
    )


async def audit_url(
    url: str,
    *,
    level: str = config.DEFAULT_LEVEL,
    include_best_practice: bool = False,
    session: BrowserSession | None = None,
) -> PageAudit:
    """Audit a single live URL."""
    owns_session = session is None
    session = session or BrowserSession()
    try:
        if owns_session:
            await session.start()
        async with session.new_page() as page:
            try:
                await axe_runner.load_page(page, url=url)
            except Exception as exc:  # navigation / timeout
                return builder.build_page_audit(
                    target=url, level=level, axe_results={}, govuk_findings=[],
                    error=f"Could not load page: {exc}",
                )
            return await _audit_loaded_page(
                page, target=url, level=level, include_best_practice=include_best_practice
            )
    except Exception as exc:  # browser launch failure etc.
        return builder.build_page_audit(
            target=url, level=level, axe_results={}, govuk_findings=[],
            error=f"Audit failed: {exc}",
        )
    finally:
        if owns_session:
            await session.close()


async def audit_html(
    html: str,
    *,
    level: str = config.DEFAULT_LEVEL,
    include_best_practice: bool = False,
    target: str = "<html-snippet>",
) -> PageAudit:
    """Audit a raw HTML string / component snippet."""
    session = BrowserSession()
    try:
        await session.start()
        async with session.new_page() as page:
            await axe_runner.load_page(page, html=html)
            return await _audit_loaded_page(
                page, target=target, level=level, include_best_practice=include_best_practice
            )
    except Exception as exc:
        return builder.build_page_audit(
            target=target, level=level, axe_results={}, govuk_findings=[],
            error=f"Audit failed: {exc}",
        )
    finally:
        await session.close()


async def audit_site(
    start_url: str,
    *,
    max_pages: int = config.DEFAULT_MAX_PAGES,
    max_depth: int = config.DEFAULT_MAX_DEPTH,
    level: str = config.DEFAULT_LEVEL,
    include_best_practice: bool = False,
) -> SiteAudit:
    """Crawl a site (same origin) and audit each page."""
    max_pages = max(1, min(max_pages, config.MAX_PAGES_CEILING))
    max_depth = max(0, min(max_depth, config.MAX_DEPTH_CEILING))
    plan = CrawlPlan(start_url, max_pages=max_pages, max_depth=max_depth)
    pages: list[PageAudit] = []

    session = BrowserSession()
    try:
        await session.start()
        while True:
            nxt = plan.next()
            if nxt is None:
                break
            url, depth = nxt
            async with session.new_page() as page:
                try:
                    await axe_runner.load_page(page, url=url)
                except Exception as exc:
                    pages.append(
                        builder.build_page_audit(
                            target=url, level=level, axe_results={}, govuk_findings=[],
                            error=f"Could not load page: {exc}",
                        )
                    )
                    continue
                pages.append(
                    await _audit_loaded_page(
                        page, target=url, level=level,
                        include_best_practice=include_best_practice,
                    )
                )
                try:
                    links = await extract_links(page, url)
                    plan.add_links(links, depth)
                except Exception:
                    pass  # link extraction is best-effort
    except Exception as exc:
        if not pages:
            pages.append(
                builder.build_page_audit(
                    target=start_url, level=level, axe_results={}, govuk_findings=[],
                    error=f"Crawl failed: {exc}",
                )
            )
    finally:
        await session.close()

    summary = builder.build_summary(pages, level)
    return SiteAudit(start_url=start_url, level=level, pages=pages, summary=summary)
