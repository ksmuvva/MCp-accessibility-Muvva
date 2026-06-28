"""GDS-style compliance summary and accessibility-statement draft.

GOV.UK accessibility statements use three compliance statuses: compliant,
partially compliant, and not compliant. This renders the computed
:class:`ComplianceSummary` into that language and drafts a statement following the
structure of the GDS model accessibility statement.
"""

from __future__ import annotations

from accessibility_mcp.reporting.models import (
    ComplianceStatus,
    ComplianceSummary,
    PageAudit,
    SiteAudit,
)
from accessibility_mcp.rules import wcag22

_STATUS_SENTENCE = {
    ComplianceStatus.COMPLIANT: "This website is compliant with the Web Content "
    "Accessibility Guidelines version 2.2 AA standard.",
    ComplianceStatus.PARTIALLY_COMPLIANT: "This website is partially compliant with the "
    "Web Content Accessibility Guidelines version 2.2 AA standard, due to the "
    "non-compliances listed below.",
    ComplianceStatus.NON_COMPLIANT: "This website is not compliant with the Web Content "
    "Accessibility Guidelines version 2.2 AA standard. The non-compliances are listed below.",
}

_STATUS_LABEL = {
    ComplianceStatus.COMPLIANT: "Compliant",
    ComplianceStatus.PARTIALLY_COMPLIANT: "Partially compliant",
    ComplianceStatus.NON_COMPLIANT: "Not compliant",
}


def render_summary(summary: ComplianceSummary) -> str:
    """Render the compliance summary as concise GDS-flavoured Markdown."""
    b = summary.impact_breakdown
    lines = [
        "## GDS compliance summary",
        "",
        f"**Status: {_STATUS_LABEL[summary.status]}** "
        f"(WCAG {summary.wcag_version} level {summary.level})",
        "",
        f"- Pages audited: {summary.pages_audited}",
        f"- Automated violations: {summary.total_violations} "
        f"(critical {b.get('critical', 0)}, serious {b.get('serious', 0)}, "
        f"moderate {b.get('moderate', 0)}, minor {b.get('minor', 0)})",
        f"- Items needing manual review: {summary.total_needs_review}",
    ]
    if summary.failing_criteria:
        lines.append(f"- Failing WCAG criteria: {', '.join(summary.failing_criteria)}")
    lines.append("")
    lines.append("**Why this status:**")
    lines.extend(f"- {r}" for r in summary.reasons)
    return "\n".join(lines)


def _failing_criteria_lines(summary: ComplianceSummary) -> list[str]:
    lines: list[str] = []
    for num in summary.failing_criteria:
        crit = wcag22.CRITERIA_BY_NUMBER.get(num)
        if crit:
            lines.append(
                f"- WCAG {num} {crit.name} (level {crit.level}). "
                f"See {crit.understanding_url}."
            )
        else:
            lines.append(f"- WCAG {num}.")
    return lines


def generate_statement(
    summary: ComplianceSummary,
    *,
    service_name: str = "[service name]",
    organisation: str = "[organisation]",
    contact_email: str = "[contact email]",
    website_url: str = "[website URL]",
    audit_date: str = "[date]",
) -> str:
    """Draft a GOV.UK-format accessibility statement from an audit summary.

    Follows the GDS model statement structure. Placeholders in [square brackets]
    must be completed by the service team before publication. This is a starting
    point, not a substitute for the full manual audit GDS requires.
    """
    status_sentence = _STATUS_SENTENCE[summary.status]
    failing = _failing_criteria_lines(summary)

    non_accessible = (
        "\n".join(failing)
        if failing
        else "- No automated WCAG failures were detected. Manual testing may still "
        "identify issues; update this section as they are found."
    )

    manual = wcag22.manual_criteria(summary.level)
    new_2_2 = ", ".join(wcag22.NEW_IN_2_2)

    return f"""# Accessibility statement for {service_name}

This accessibility statement applies to {website_url}.

This website is run by {organisation}. We want as many people as possible to be
able to use this website.

## Compliance status

{status_sentence}

## Non-accessible content

The content listed below is non-accessible for the following reasons.

### Non-compliance with the accessibility regulations

{non_accessible}

## How we tested this website

This website was last tested on {audit_date}. Testing was carried out using
automated tooling (axe-core via the Accessibility MCP server) against WCAG
{summary.wcag_version} level {summary.level}, covering {summary.pages_audited}
page(s).

**Important:** automated testing detects only part of WCAG (roughly 30–40% of
issues). The following require manual assessment and are not covered by this
automated test:

- {len(manual)} WCAG {summary.level} criteria that cannot be fully automated
  (for example keyboard operation, focus order, captions and reflow).
- The criteria new in WCAG 2.2: {new_2_2}.

A full manual audit must be completed before claiming compliance.

## Feedback and contact information

If you find any accessibility problems not listed on this page, or you need
information in a different format, contact: {contact_email}.

## Enforcement procedure

The Equality and Human Rights Commission (EHRC) is responsible for enforcing the
Public Sector Bodies (Websites and Mobile Applications) (No. 2) Accessibility
Regulations 2018 (the ‘accessibility regulations’). If you’re not happy with how
we respond to your complaint, contact the Equality Advisory and Support Service
(EASS).

_This statement was drafted automatically from an accessibility audit on
{audit_date} and must be reviewed and completed before publication._
"""


def summary_from(audit: PageAudit | SiteAudit) -> ComplianceSummary:
    """Extract the ComplianceSummary from either audit type."""
    if isinstance(audit, SiteAudit):
        return audit.summary
    from accessibility_mcp.reporting.builder import build_summary

    return build_summary([audit], audit.level)
