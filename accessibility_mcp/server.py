"""Accessibility MCP server — WCAG 2.2 AA auditing aligned with the GOV.UK standard.

Exposes five tools over the Model Context Protocol (stdio transport):

  * audit_url                        — audit one live page
  * audit_html                       — audit a raw HTML string / component
  * audit_site                       — crawl a site and audit each page
  * list_wcag_rules                  — catalogue of checked WCAG 2.2 criteria
  * generate_accessibility_statement — draft a GOV.UK-format statement

Each audit tool returns structured JSON, a human-readable Markdown report and a
GDS-style compliance summary, plus an ``audit_id`` that can be fed to
``generate_accessibility_statement``.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from typing import Any

from mcp.server.fastmcp import FastMCP

from accessibility_mcp import audit as audit_engine
from accessibility_mcp import config
from accessibility_mcp.reporting import gds_summary, json_report, markdown_report
from accessibility_mcp.reporting.models import PageAudit, SiteAudit
from accessibility_mcp.rules import wcag22

mcp = FastMCP("accessibility-mcp")

# Small in-memory cache of recent audits so generate_accessibility_statement can
# reuse a prior result by id (avoids re-crawling). Bounded to avoid unbounded growth.
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


@mcp.tool()
async def audit_url(
    url: str,
    level: str = "AA",
    include_best_practice: bool = False,
) -> dict[str, Any]:
    """Audit a single live web page for WCAG 2.2 accessibility (GOV.UK standard).

    Loads the URL in headless Chromium, runs axe-core restricted to the chosen
    conformance level plus GOV.UK-specific checks, and returns structured JSON, a
    Markdown report and a GDS-style compliance summary.

    Args:
        url: The page URL to audit (http/https).
        level: WCAG conformance level: "A", "AA" (default, GOV.UK requirement) or "AAA".
        include_best_practice: Also run axe "best-practice" rules (not WCAG, but
            commonly flagged by GDS reviewers).
    """
    result = await audit_engine.audit_url(
        url, level=level, include_best_practice=include_best_practice
    )
    return _page_payload(result)


@mcp.tool()
async def audit_html(
    html: str,
    level: str = "AA",
    include_best_practice: bool = False,
) -> dict[str, Any]:
    """Audit a raw HTML string or component snippet for WCAG 2.2 accessibility.

    Renders the HTML in headless Chromium (no network fetch) and audits it. Useful
    for testing templates or components in isolation, e.g. in CI before deploy.

    Args:
        html: The HTML markup to audit.
        level: WCAG conformance level: "A", "AA" (default) or "AAA".
        include_best_practice: Also run axe "best-practice" rules.
    """
    result = await audit_engine.audit_html(
        html, level=level, include_best_practice=include_best_practice
    )
    return _page_payload(result)


@mcp.tool()
async def audit_site(
    url: str,
    max_pages: int = 20,
    max_depth: int = 2,
    level: str = "AA",
    include_best_practice: bool = False,
) -> dict[str, Any]:
    """Crawl a site (same origin) and audit each page for WCAG 2.2 accessibility.

    Performs a breadth-first crawl from the start URL, staying on the same origin,
    and audits every page up to the page/depth limits. Returns per-page results and
    an aggregated service-level GDS compliance summary.

    Args:
        url: The start URL to crawl from.
        max_pages: Maximum pages to audit (capped by server config).
        max_depth: Maximum link depth from the start URL (capped by server config).
        level: WCAG conformance level: "A", "AA" (default) or "AAA".
        include_best_practice: Also run axe "best-practice" rules.
    """
    result = await audit_engine.audit_site(
        url,
        max_pages=max_pages,
        max_depth=max_depth,
        level=level,
        include_best_practice=include_best_practice,
    )
    return _site_payload(result)


@mcp.tool()
def list_wcag_rules(version: str = "2.2", level: str = "AA") -> dict[str, Any]:
    """List the WCAG success criteria this server checks, with automation coverage.

    Returns each criterion's number, name, level, whether it is fully/partially/not
    automatable, whether it is new in WCAG 2.2, and its W3C Understanding URL. Use
    this to see what automated auditing can and cannot verify.

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

    Provide either ``audit_id`` (from a previous audit_* call this session) or a
    ``url`` to audit fresh. Returns a Markdown statement following the GDS model
    structure, with placeholders for details the service team must complete.

    Args:
        audit_id: Id returned by a previous audit tool call.
        url: URL to audit now if no audit_id is given.
        service_name: Name of the service (fills the statement heading).
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
        summary,
        service_name=service_name,
        organisation=organisation,
        contact_email=contact_email,
        website_url=website_url,
        audit_date=audit_date,
    )
    return {
        "status": summary.status.value,
        "statement_markdown": statement,
        "gds_summary": gds_summary.render_summary(summary),
    }


def main() -> None:
    """Console-script entry point: run the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
