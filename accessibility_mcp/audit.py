"""High-level audit orchestration (multi-engine, interactive).

Ties together the Playwright browser, axe-core (in-process), the GOV.UK custom
checks and the Node engine runner (pa11y / Lighthouse / IBM). Returns fully-built
:class:`PageAudit` / :class:`SiteAudit` models. Engine and page errors are captured
into the model rather than raised, so one bad page or engine never breaks a run.
"""

from __future__ import annotations

from accessibility_mcp import config
from accessibility_mcp.engine import axe_runner, node_bridge
from accessibility_mcp.engine.browser import BrowserSession, apply_steps
from accessibility_mcp.engine.crawler import CrawlPlan, extract_links
from accessibility_mcp.reporting import builder
from accessibility_mcp.reporting.models import Finding, PageAudit, SiteAudit
from accessibility_mcp.rules import govuk_checks, normalize


def _resolve_engines(engines: list[str] | None) -> list[str]:
    if not engines:
        return list(config.DEFAULT_ENGINES)
    return [e for e in engines if e in config.ALL_ENGINES] or list(config.DEFAULT_ENGINES)


async def _run_node_engines(
    engines: list[str],
    *,
    url: str | None,
    html: str | None,
    steps: list[dict] | None,
    cookies: list[dict] | None,
) -> tuple[list[Finding], dict[str, str]]:
    """Run requested Node engines and return (findings, engine_errors)."""
    node_engines = [e for e in engines if e in config.NODE_ENGINES]
    if not node_engines:
        return [], {}
    raw = await node_bridge.run_node_engines(
        node_engines, url=url, html=html, steps=steps, cookies=cookies
    )
    findings: list[Finding] = []
    errors: dict[str, str] = {}
    for name, res in raw.get("engines", {}).items():
        if res.get("ok"):
            findings.extend(normalize.normalize_engine(name, res))
        else:
            errors[name] = res.get("error", "unknown error")
    return findings, errors


async def _audit_loaded_page(
    page,
    *,
    target: str,
    level: str,
    include_best_practice: bool,
    engines: list[str],
    steps: list[dict] | None,
    url: str | None,
    html: str | None,
) -> PageAudit:
    """Run all requested engines on an already-navigated page and build the audit."""
    await apply_steps(page, steps)

    # axe-core (in-process) on the live, post-interaction page.
    axe_results: dict = {}
    if "axe" in engines:
        tags = config.axe_tags(level=level, include_best_practice=include_best_practice)
        axe_results = await axe_runner.run_axe(page, tags)

    page_html = await page.content()
    govuk_findings = govuk_checks.run_govuk_checks(page_html)

    cookies = await page.context.cookies()
    extra_findings, engine_errors = await _run_node_engines(
        engines, url=url, html=html, steps=steps, cookies=cookies
    )

    return builder.build_page_audit(
        target=target,
        level=level,
        axe_results=axe_results,
        govuk_findings=govuk_findings,
        extra_findings=extra_findings,
        engines_used=engines,
        engine_errors=engine_errors,
        axe_version=axe_runner.axe_engine_version(),
    )


async def audit_rule_on_page(page, rule_id: str, *, level: str = config.DEFAULT_LEVEL) -> PageAudit:
    """Run a single axe-core rule against an already-open page."""
    results = await axe_runner.run_axe_rules(page, [rule_id])
    return builder.build_page_audit(
        target=page.url, level=level, axe_results=results, govuk_findings=[],
        engines_used=["axe"], axe_version=axe_runner.axe_engine_version(),
    )


async def audit_rule(
    rule_id: str,
    *,
    url: str | None = None,
    html: str | None = None,
    level: str = config.DEFAULT_LEVEL,
) -> PageAudit:
    """Run a single axe-core rule against a URL or HTML snippet."""
    target = url or "<html-snippet>"
    session = BrowserSession()
    try:
        await session.start()
        async with session.new_page() as page:
            try:
                await axe_runner.load_page(page, url=url, html=html)
            except Exception as exc:
                return builder.build_page_audit(
                    target=target, level=level, axe_results={}, govuk_findings=[],
                    engines_used=["axe"], error=f"Could not load target: {exc}",
                )
            return await audit_rule_on_page(page, rule_id, level=level)
    except Exception as exc:
        return builder.build_page_audit(
            target=target, level=level, axe_results={}, govuk_findings=[],
            engines_used=["axe"], error=f"Audit failed: {exc}",
        )
    finally:
        await session.close()


async def audit_open_page(
    page,
    *,
    level: str = config.DEFAULT_LEVEL,
    include_best_practice: bool = False,
    engines: list[str] | None = None,
) -> PageAudit:
    """Audit an already-open, possibly post-interaction page (stateful session).

    Node engines (pa11y/Lighthouse) re-load the current URL, so they reflect the
    URL's initial state; axe-core and IBM see the live interactive state.
    """
    engines = _resolve_engines(engines)
    return await _audit_loaded_page(
        page, target=page.url, level=level,
        include_best_practice=include_best_practice,
        engines=engines, steps=None, url=page.url, html=None,
    )


async def audit_url(
    url: str,
    *,
    level: str = config.DEFAULT_LEVEL,
    include_best_practice: bool = False,
    engines: list[str] | None = None,
    steps: list[dict] | None = None,
    session: BrowserSession | None = None,
) -> PageAudit:
    """Audit a single live URL with the chosen engines."""
    engines = _resolve_engines(engines)
    owns_session = session is None
    session = session or BrowserSession()
    try:
        if owns_session:
            await session.start()
        async with session.new_page() as page:
            try:
                await axe_runner.load_page(page, url=url)
            except Exception as exc:
                return builder.build_page_audit(
                    target=url, level=level, axe_results={}, govuk_findings=[],
                    engines_used=engines, error=f"Could not load page: {exc}",
                )
            return await _audit_loaded_page(
                page, target=url, level=level, include_best_practice=include_best_practice,
                engines=engines, steps=steps, url=url, html=None,
            )
    except Exception as exc:
        return builder.build_page_audit(
            target=url, level=level, axe_results={}, govuk_findings=[],
            engines_used=engines, error=f"Audit failed: {exc}",
        )
    finally:
        if owns_session:
            await session.close()


async def audit_html(
    html: str,
    *,
    level: str = config.DEFAULT_LEVEL,
    include_best_practice: bool = False,
    engines: list[str] | None = None,
    steps: list[dict] | None = None,
    target: str = "<html-snippet>",
) -> PageAudit:
    """Audit a raw HTML string / component snippet with the chosen engines."""
    engines = _resolve_engines(engines)
    session = BrowserSession()
    try:
        await session.start()
        async with session.new_page() as page:
            await axe_runner.load_page(page, html=html)
            return await _audit_loaded_page(
                page, target=target, level=level, include_best_practice=include_best_practice,
                engines=engines, steps=steps, url=None, html=html,
            )
    except Exception as exc:
        return builder.build_page_audit(
            target=target, level=level, axe_results={}, govuk_findings=[],
            engines_used=engines, error=f"Audit failed: {exc}",
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
    engines: list[str] | None = None,
) -> SiteAudit:
    """Crawl a site (same origin) and audit each page with the chosen engines."""
    engines = _resolve_engines(engines)
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
                            engines_used=engines, error=f"Could not load page: {exc}",
                        )
                    )
                    continue
                pages.append(
                    await _audit_loaded_page(
                        page, target=url, level=level,
                        include_best_practice=include_best_practice,
                        engines=engines, steps=None, url=url, html=None,
                    )
                )
                try:
                    links = await extract_links(page, url)
                    plan.add_links(links, depth)
                except Exception:
                    pass
    except Exception as exc:
        if not pages:
            pages.append(
                builder.build_page_audit(
                    target=start_url, level=level, axe_results={}, govuk_findings=[],
                    engines_used=engines, error=f"Crawl failed: {exc}",
                )
            )
    finally:
        await session.close()

    summary = builder.build_summary(pages, level)
    return SiteAudit(start_url=start_url, level=level, pages=pages, summary=summary)
