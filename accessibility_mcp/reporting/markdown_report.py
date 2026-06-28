"""Human-readable Markdown reports.

Renders a PageAudit (or SiteAudit) into a report grouped by severity, with the
WCAG criteria, remediation, and references for each finding. Designed to be
readable both in a terminal MCP client and when pasted into a ticket.
"""

from __future__ import annotations

from accessibility_mcp.reporting.models import (
    Finding,
    Outcome,
    PageAudit,
    SiteAudit,
)

_STATUS_LABEL = {
    "compliant": "Compliant",
    "partially_compliant": "Partially compliant",
    "non_compliant": "Not compliant",
}


def _finding_block(f: Finding) -> str:
    crit = ", ".join(f.wcag_criteria) if f.wcag_criteria else "—"
    impact = f.impact.value if f.impact else "n/a"
    lines = [
        f"- **{f.id}** ({f.source}, impact: {impact}) — WCAG {crit}",
        f"  - {f.help or f.description}",
        f"  - _Fix_: {f.remediation}" if f.remediation else "",
        f"  - Affected elements: {f.node_count}" if f.nodes else "",
    ]
    refs = []
    if f.help_url:
        refs.append(f"[details]({f.help_url})")
    if f.technique_url:
        refs.append(f"[WCAG technique]({f.technique_url})")
    if f.govuk_reference:
        refs.append(f"[GOV.UK]({f.govuk_reference})")
    if refs:
        lines.append(f"  - {' · '.join(refs)}")
    return "\n".join(line for line in lines if line)


def _section(title: str, findings: list[Finding]) -> str:
    if not findings:
        return ""
    body = "\n".join(_finding_block(f) for f in findings)
    return f"\n### {title} ({len(findings)})\n\n{body}\n"


def render_page(audit: PageAudit) -> str:
    if not audit.ok:
        return f"# Accessibility audit — {audit.target}\n\n**Audit failed:** {audit.error}\n"

    breakdown = audit.impact_breakdown()
    parts = [
        f"# Accessibility audit — {audit.target}",
        "",
        f"- WCAG {audit.wcag_version} level **{audit.level}** · axe-core {audit.axe_version}",
        f"- Violations: **{audit.violation_count}** "
        f"(critical {breakdown['critical']}, serious {breakdown['serious']}, "
        f"moderate {breakdown['moderate']}, minor {breakdown['minor']})",
        f"- Needs manual review: **{audit.needs_review_count}**",
        f"- Automated checks passed: **{len(audit.passes)}**",
        "",
        "> Automated testing detects roughly 30–40% of WCAG issues. Items below that "
        "passed or are not listed still require manual assessment to confirm "
        "conformance.",
    ]
    parts.append(_section("❌ Violations", audit.violations))
    parts.append(_section("⚠️ Needs manual review", audit.needs_review))
    return "\n".join(p for p in parts if p is not None)


def render_site(audit: SiteAudit) -> str:
    s = audit.summary
    parts = [
        f"# Accessibility audit — {audit.start_url} (site)",
        "",
        f"- Pages audited: **{s.pages_audited}**",
        f"- Overall status: **{_STATUS_LABEL.get(s.status.value, s.status.value)}**",
        f"- Total violations: **{s.total_violations}** · needs review: **{s.total_needs_review}**",
        "",
        "## Per-page results",
    ]
    for p in audit.pages:
        if p.ok:
            parts.append(
                f"- {p.target} — {p.violation_count} violations, "
                f"{p.needs_review_count} need review"
            )
        else:
            parts.append(f"- {p.target} — audit failed: {p.error}")
    parts.append("")
    parts.append("## Detail")
    for p in audit.pages:
        parts.append(render_page(p))
        parts.append("\n---\n")
    return "\n".join(parts)
