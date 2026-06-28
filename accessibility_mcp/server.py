"""Accessibility MCP server — WCAG 2.2 AA auditing aligned with the GOV.UK standard.

Exposes (over stdio):

  Bundled audits (multi-engine):
    audit_url, audit_html, audit_site

  Interactive navigation (stateful browser session):
    browser_open, browser_navigate, browser_click, browser_fill, browser_wait,
    browser_snapshot, audit_current_page, browser_close

  Per-axe-rule tools (~100, one per axe-core rule) — optional, on by default:
    axe_<rule_id>, e.g. axe_color_contrast

  Catalogue / reporting:
    list_wcag_rules, list_axe_rules, list_engines, generate_accessibility_statement

Engines: axe-core (in-process) plus pa11y, Lighthouse and IBM Equal Access via a
Node subprocess. Each audit tool returns structured JSON, a Markdown report and a
GDS-style compliance summary.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from typing import Any

from mcp.server.fastmcp import FastMCP

from accessibility_mcp import audit as audit_engine
from accessibility_mcp import config
from accessibility_mcp.engine import session as session_mod
from accessibility_mcp.reporting import gds_summary, json_report, markdown_report
from accessibility_mcp.reporting.models import PageAudit, SiteAudit
from accessibility_mcp.rules import axe_rules, groups, wcag22

mcp = FastMCP("accessibility-mcp")

# ----------------------------------------------------------------------------- #
# Audit result cache (for generate_accessibility_statement by audit_id)
# ----------------------------------------------------------------------------- #

_AUDIT_CACHE: "OrderedDict[str, PageAudit | SiteAudit]" = OrderedDict()
_CACHE_MAX = 50


def _cache_audit(result: PageAudit | SiteAudit) -> str:
    audit_id = uuid.uuid4().hex[:12]
    _AUDIT_CACHE[audit_id] = result
    while len(_AUDIT_CACHE) > _CACHE_MAX:
        _AUDIT_CACHE.popitem(last=False)
    return audit_id


def _page_payload(result: PageAudit) -> dict[str, Any]:
    summary = gds_summary.summary_from(result)
    audit_id = _cache_audit(result)
    return {
        "audit_id": audit_id,
        "target": result.target,
        "status": summary.status.value,
        "engines_used": result.engines_used,
        "engine_errors": result.engine_errors,
        "json": json_report.page_to_dict(result),
        "markdown_report": markdown_report.render_page(result),
        "gds_summary": gds_summary.render_summary(summary),
    }


def _site_payload(result: SiteAudit) -> dict[str, Any]:
    audit_id = _cache_audit(result)
    return {
        "audit_id": audit_id,
        "start_url": result.start_url,
        "status": result.summary.status.value,
        "json": json_report.site_to_dict(result),
        "markdown_report": markdown_report.render_site(result),
        "gds_summary": gds_summary.render_summary(result.summary),
    }


# ----------------------------------------------------------------------------- #
# Bundled multi-engine audit tools
# ----------------------------------------------------------------------------- #


@mcp.tool()
async def audit_url(
    url: str,
    level: str = "AA",
    engines: list[str] | None = None,
    steps: list[dict] | None = None,
    include_best_practice: bool = False,
) -> dict[str, Any]:
    """Audit a single live web page for WCAG 2.2 accessibility (GOV.UK standard).

    Loads the URL in headless Chromium, optionally performs interaction `steps`
    first, then runs the chosen `engines` plus GOV.UK-specific checks. Returns
    structured JSON, a Markdown report and a GDS-style compliance summary.

    Args:
        url: The page URL to audit (http/https).
        level: WCAG level: "A", "AA" (default, GOV.UK requirement) or "AAA".
        engines: Subset of ["axe","pa11y","lighthouse","ibm"]. Defaults to ["axe"].
        steps: Optional interactions before auditing, each
            {"action": "click|fill|wait|press|navigate", "selector": ..., "value": ..., "ms": ...}.
        include_best_practice: Also run axe "best-practice" rules (not WCAG).
    """
    result = await audit_engine.audit_url(
        url, level=level, engines=engines, steps=steps,
        include_best_practice=include_best_practice,
    )
    return _page_payload(result)


@mcp.tool()
async def audit_html(
    html: str,
    level: str = "AA",
    engines: list[str] | None = None,
    steps: list[dict] | None = None,
    include_best_practice: bool = False,
) -> dict[str, Any]:
    """Audit a raw HTML string or component snippet for WCAG 2.2 accessibility.

    Renders the HTML in headless Chromium (no network fetch) and audits it with the
    chosen engines. Useful for testing templates/components in CI.

    Args:
        html: The HTML markup to audit.
        level: WCAG level: "A", "AA" (default) or "AAA".
        engines: Subset of ["axe","pa11y","lighthouse","ibm"]. Defaults to ["axe"].
        steps: Optional interactions before auditing (see audit_url).
        include_best_practice: Also run axe "best-practice" rules.
    """
    result = await audit_engine.audit_html(
        html, level=level, engines=engines, steps=steps,
        include_best_practice=include_best_practice,
    )
    return _page_payload(result)


@mcp.tool()
async def audit_site(
    url: str,
    max_pages: int = 20,
    max_depth: int = 2,
    level: str = "AA",
    engines: list[str] | None = None,
    include_best_practice: bool = False,
) -> dict[str, Any]:
    """Crawl a site (same origin) and audit each page for WCAG 2.2 accessibility.

    Breadth-first crawl from the start URL, auditing each page with the chosen
    engines. Returns per-page results and an aggregated service-level GDS summary.

    Args:
        url: The start URL to crawl from.
        max_pages: Maximum pages to audit (capped by server config).
        max_depth: Maximum link depth from the start URL (capped by server config).
        level: WCAG level: "A", "AA" (default) or "AAA".
        engines: Subset of ["axe","pa11y","lighthouse","ibm"]. Defaults to ["axe"].
        include_best_practice: Also run axe "best-practice" rules.
    """
    result = await audit_engine.audit_site(
        url, max_pages=max_pages, max_depth=max_depth, level=level,
        engines=engines, include_best_practice=include_best_practice,
    )
    return _site_payload(result)


# ----------------------------------------------------------------------------- #
# Dedicated single-engine tools
# ----------------------------------------------------------------------------- #


async def _audit_single_engine(
    engine: str,
    *,
    url: str,
    html: str,
    session_id: str,
    level: str,
    include_best_practice: bool = False,
) -> dict[str, Any]:
    """Audit a url / html / session_id with exactly one engine."""
    if session_id:
        session = session_mod.manager.get(session_id)
        if session is None:
            return {"error": f"Unknown session_id '{session_id}'."}
        result = await audit_engine.audit_open_page(
            session.page, level=level, engines=[engine],
            include_best_practice=include_best_practice,
        )
    elif url:
        result = await audit_engine.audit_url(
            url, level=level, engines=[engine], include_best_practice=include_best_practice,
        )
    elif html:
        result = await audit_engine.audit_html(
            html, level=level, engines=[engine], include_best_practice=include_best_practice,
        )
    else:
        return {"error": "Provide one of: url, html, or session_id."}
    return _page_payload(result)


@mcp.tool()
async def audit_axe(
    url: str = "", html: str = "", session_id: str = "",
    level: str = "AA", include_best_practice: bool = False,
) -> dict[str, Any]:
    """Audit with the axe-core engine only (plus GOV.UK checks).

    Provide one of: url, html, or session_id. axe-core is the in-process engine
    with explicit WCAG 2.2 rule tags.
    """
    return await _audit_single_engine(
        "axe", url=url, html=html, session_id=session_id, level=level,
        include_best_practice=include_best_practice,
    )


@mcp.tool()
async def audit_pa11y(url: str = "", html: str = "", session_id: str = "", level: str = "AA") -> dict[str, Any]:
    """Audit with the pa11y engine only (HTML_CodeSniffer + axe runners).

    Provide one of: url, html, or session_id. Requires the Node engine runner
    (accessibility_mcp/engines_node/setup.sh).
    """
    return await _audit_single_engine("pa11y", url=url, html=html, session_id=session_id, level=level)


@mcp.tool()
async def audit_lighthouse(url: str = "", html: str = "", session_id: str = "", level: str = "AA") -> dict[str, Any]:
    """Audit with the Google Lighthouse accessibility engine only.

    Provide one of: url, html, or session_id. Lighthouse audits by URL (it reloads
    the page). Requires the Node engine runner.
    """
    return await _audit_single_engine("lighthouse", url=url, html=html, session_id=session_id, level=level)


@mcp.tool()
async def audit_ibm(url: str = "", html: str = "", session_id: str = "", level: str = "AA") -> dict[str, Any]:
    """Audit with the IBM Equal Access engine only.

    Provide one of: url, html, or session_id. Requires the Node engine runner and
    network egress to the IBM rule archive (cdn.jsdelivr.net); otherwise returns a
    structured engine-error.
    """
    return await _audit_single_engine("ibm", url=url, html=html, session_id=session_id, level=level)


# ----------------------------------------------------------------------------- #
# Interactive navigation (stateful session)
# ----------------------------------------------------------------------------- #


@mcp.tool()
async def browser_open() -> dict[str, Any]:
    """Open a new stateful browser session and return its session_id.

    Use the session_id with browser_navigate / browser_click / browser_fill /
    browser_wait / browser_snapshot / audit_current_page, then browser_close.
    Lets you audit pages behind logins or multi-step journeys.
    """
    session = await session_mod.manager.open()
    return {"session_id": session.id, "active_sessions": session_mod.manager.count}


@mcp.tool()
async def browser_navigate(session_id: str, url: str) -> dict[str, Any]:
    """Navigate a session's page to a URL."""
    session = session_mod.manager.get(session_id)
    if session is None:
        return {"error": f"Unknown session_id '{session_id}'. Call browser_open first."}
    await session.page.goto(url, wait_until="load")
    return {"session_id": session_id, "url": session.page.url, "title": await session.page.title()}


@mcp.tool()
async def browser_click(session_id: str, selector: str) -> dict[str, Any]:
    """Click an element (CSS selector) in a session's page."""
    session = session_mod.manager.get(session_id)
    if session is None:
        return {"error": f"Unknown session_id '{session_id}'."}
    await session.page.click(selector)
    return {"session_id": session_id, "url": session.page.url}


@mcp.tool()
async def browser_fill(session_id: str, selector: str, value: str) -> dict[str, Any]:
    """Fill a form field (CSS selector) with a value in a session's page."""
    session = session_mod.manager.get(session_id)
    if session is None:
        return {"error": f"Unknown session_id '{session_id}'."}
    await session.page.fill(selector, value)
    return {"session_id": session_id, "url": session.page.url}


@mcp.tool()
async def browser_wait(session_id: str, selector: str = "", ms: int = 0) -> dict[str, Any]:
    """Wait for a selector to appear, or for a number of milliseconds."""
    session = session_mod.manager.get(session_id)
    if session is None:
        return {"error": f"Unknown session_id '{session_id}'."}
    if selector:
        await session.page.wait_for_selector(selector)
    elif ms:
        await session.page.wait_for_timeout(ms)
    return {"session_id": session_id, "url": session.page.url}


@mcp.tool()
async def browser_snapshot(session_id: str) -> dict[str, Any]:
    """Return the current url, title and visible text of a session's page."""
    session = session_mod.manager.get(session_id)
    if session is None:
        return {"error": f"Unknown session_id '{session_id}'."}
    text = await session.page.inner_text("body")
    return {
        "session_id": session_id,
        "url": session.page.url,
        "title": await session.page.title(),
        "text": text[:4000],
    }


@mcp.tool()
async def audit_current_page(
    session_id: str,
    level: str = "AA",
    engines: list[str] | None = None,
    include_best_practice: bool = False,
) -> dict[str, Any]:
    """Audit the current (post-interaction) state of a session's page.

    axe-core runs against the live page; pa11y, Lighthouse and IBM audit a
    serialised snapshot of the current DOM, so interaction state (filled fields,
    opened modals, dynamic content) is preserved.

    Args:
        session_id: A session from browser_open.
        level: WCAG level: "A", "AA" (default) or "AAA".
        engines: Subset of ["axe","pa11y","lighthouse","ibm"]. Defaults to ["axe"].
        include_best_practice: Also run axe "best-practice" rules.
    """
    session = session_mod.manager.get(session_id)
    if session is None:
        return {"error": f"Unknown session_id '{session_id}'."}
    result = await audit_engine.audit_open_page(
        session.page, level=level, engines=engines,
        include_best_practice=include_best_practice,
    )
    return _page_payload(result)


@mcp.tool()
async def browser_close(session_id: str) -> dict[str, Any]:
    """Close a stateful browser session and free its resources."""
    closed = await session_mod.manager.close(session_id)
    return {"closed": closed, "active_sessions": session_mod.manager.count}


# ----------------------------------------------------------------------------- #
# Catalogue / reporting tools
# ----------------------------------------------------------------------------- #


@mcp.tool()
def list_engines() -> dict[str, Any]:
    """List the available audit engines and whether the Node engines are installed."""
    return {
        "engines": {
            "axe": {"language": "python", "available": True,
                    "description": "Deque axe-core, WCAG 2.2 tags (in-process)."},
            "pa11y": {"language": "node", "available": config.node_engines_available(),
                      "description": "pa11y with HTML_CodeSniffer + axe runners."},
            "lighthouse": {"language": "node", "available": config.node_engines_available(),
                           "description": "Google Lighthouse accessibility category."},
            "ibm": {"language": "node", "available": config.node_engines_available(),
                    "description": "IBM Equal Access (needs egress to its rule archive)."},
        },
        "default_engines": config.DEFAULT_ENGINES,
        "node_runner_installed": config.node_engines_available(),
    }


@mcp.tool()
def list_wcag_rules(version: str = "2.2", level: str = "AA") -> dict[str, Any]:
    """List the WCAG success criteria checked, with automation coverage.

    Returns each criterion's number, name, level, automation (full/partial/manual),
    whether it is new in WCAG 2.2, and its W3C Understanding URL.

    Args:
        version: WCAG version (informational; this server targets 2.2).
        level: Highest conformance level to include: "A" or "AA" (default).
    """
    crits = wcag22.criteria(level)
    return {
        "wcag_version": "2.2",
        "level": level.upper(),
        "total": len(crits),
        "new_in_2_2": wcag22.NEW_IN_2_2,
        "automation_legend": {
            "full": "Automated tools reliably detect failures.",
            "partial": "Tools catch some failures; a human must confirm.",
            "manual": "Not machine-detectable; requires human assessment.",
        },
        "criteria": [c.to_dict() for c in crits],
    }


@mcp.tool()
def list_axe_rules(wcag_only: bool = False) -> dict[str, Any]:
    """List the axe-core rules, each of which is also exposed as its own tool.

    Args:
        wcag_only: If true, only rules tagged with a WCAG conformance level.
    """
    rules = axe_rules.wcag_rules() if wcag_only else axe_rules.all_rules()
    return {
        "axe_version": axe_rules.axe_version(),
        "per_rule_tools_enabled": config.PER_RULE_TOOLS,
        "total": len(rules),
        "rules": [r.to_dict() for r in rules],
    }


@mcp.tool()
def list_groups() -> dict[str, Any]:
    """List the grouped audit tools and which axe rules each runs.

    Two grouping schemes: by WCAG principle (audit_perceivable / audit_operable /
    audit_understandable / audit_robust) and by axe category (audit_group_<cat>).
    """
    principle = groups.principle_groups()
    category = groups.category_groups()
    return {
        "group_tools_enabled": config.GROUP_TOOLS,
        "wcag_principle_groups": {
            f"audit_{name}": {"rule_count": len(ids), "rules": ids}
            for name, ids in principle.items()
        },
        "axe_category_groups": {
            groups.category_tool_name(cat): {"category": cat, "rule_count": len(ids), "rules": ids}
            for cat, ids in sorted(category.items())
        },
    }


@mcp.tool()
async def generate_accessibility_statement(
    audit_id: str = "",
    url: str = "",
    service_name: str = "[service name]",
    organisation: str = "[organisation]",
    contact_email: str = "[contact email]",
    website_url: str = "[website URL]",
    audit_date: str = "[date]",
) -> dict[str, Any]:
    """Draft a GOV.UK-format accessibility statement from an audit.

    Provide either audit_id (from a previous audit tool call) or url (to audit now).

    Args:
        audit_id: Id returned by a previous audit tool call.
        url: URL to audit now if no audit_id is given.
        service_name: Name of the service (statement heading).
        organisation: Organisation running the website.
        contact_email: Accessibility contact email.
        website_url: The website/service URL the statement covers.
        audit_date: Date the audit was carried out.
    """
    result: PageAudit | SiteAudit | None = None
    if audit_id:
        result = _AUDIT_CACHE.get(audit_id)
        if result is None:
            return {"error": f"Unknown audit_id '{audit_id}'. Run an audit first."}
    elif url:
        result = await audit_engine.audit_url(url, level="AA")
        if website_url == "[website URL]":
            website_url = url
    else:
        return {"error": "Provide either 'audit_id' or 'url'."}

    summary = gds_summary.summary_from(result)
    statement = gds_summary.generate_statement(
        summary, service_name=service_name, organisation=organisation,
        contact_email=contact_email, website_url=website_url, audit_date=audit_date,
    )
    return {
        "status": summary.status.value,
        "statement_markdown": statement,
        "gds_summary": gds_summary.render_summary(summary),
    }


# ----------------------------------------------------------------------------- #
# Per-axe-rule tools (one MCP tool per axe-core rule)
# ----------------------------------------------------------------------------- #


def _make_rule_tool(rule: axe_rules.AxeRule):
    async def tool(url: str = "", html: str = "", session_id: str = "") -> dict[str, Any]:
        if session_id:
            session = session_mod.manager.get(session_id)
            if session is None:
                return {"error": f"Unknown session_id '{session_id}'."}
            result = await audit_engine.audit_rule_on_page(session.page, rule.rule_id)
        elif url:
            result = await audit_engine.audit_rule(rule.rule_id, url=url)
        elif html:
            result = await audit_engine.audit_rule(rule.rule_id, html=html)
        else:
            return {"error": "Provide one of: url, html, or session_id."}
        return _page_payload(result)

    tool.__name__ = rule.tool_name
    return tool


def _register_per_rule_tools() -> int:
    if not config.PER_RULE_TOOLS:
        return 0
    count = 0
    for rule in axe_rules.all_rules():
        crit = ", ".join(rule.wcag_criteria) or "no WCAG mapping"
        description = (
            f"Check ONLY the axe-core rule '{rule.rule_id}' (WCAG {crit}). "
            f"{rule.help}. Provide one of: url, html, or session_id."
        )
        mcp.add_tool(_make_rule_tool(rule), name=rule.tool_name, description=description)
        count += 1
    return count


_PER_RULE_COUNT = _register_per_rule_tools()


# ----------------------------------------------------------------------------- #
# Grouped audit tools (WCAG principle + axe category)
# ----------------------------------------------------------------------------- #


def _make_group_tool(rule_ids: list[str]):
    async def tool(
        url: str = "", html: str = "", session_id: str = "", level: str = "AA"
    ) -> dict[str, Any]:
        if session_id:
            session = session_mod.manager.get(session_id)
            if session is None:
                return {"error": f"Unknown session_id '{session_id}'."}
            result = await audit_engine.audit_rules_on_page(session.page, rule_ids, level=level)
        elif url:
            result = await audit_engine.audit_rules(rule_ids, url=url, level=level)
        elif html:
            result = await audit_engine.audit_rules(rule_ids, html=html, level=level)
        else:
            return {"error": "Provide one of: url, html, or session_id."}
        return _page_payload(result)

    return tool


def _register_group_tools() -> int:
    if not config.GROUP_TOOLS:
        return 0
    count = 0
    # WCAG principle groups: audit_perceivable / operable / understandable / robust.
    for name, ids in groups.principle_groups().items():
        tool = _make_group_tool(ids)
        tool.__name__ = f"audit_{name}"
        description = (
            f"Audit the WCAG '{name.capitalize()}' principle: runs the {len(ids)} "
            f"axe rules mapped to WCAG {name} criteria. Provide one of: url, html, "
            "or session_id."
        )
        mcp.add_tool(tool, name=f"audit_{name}", description=description)
        count += 1
    # axe category groups: audit_group_<category>.
    for category, ids in groups.category_groups().items():
        tool_name = groups.category_tool_name(category)
        tool = _make_group_tool(ids)
        tool.__name__ = tool_name
        description = (
            f"Audit the '{category}' rule group ({len(ids)} axe rules). "
            "Provide one of: url, html, or session_id."
        )
        mcp.add_tool(tool, name=tool_name, description=description)
        count += 1
    return count


_GROUP_COUNT = _register_group_tools()


def main() -> None:
    """Console-script entry point: run the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
