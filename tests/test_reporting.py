"""Unit tests for the reporting layer (builder, summary, renderers)."""

from __future__ import annotations

from accessibility_mcp.reporting import builder, gds_summary, markdown_report
from accessibility_mcp.reporting.models import ComplianceStatus, Outcome

# A minimal fake axe result with one violation and one incomplete item.
FAKE_AXE = {
    "violations": [
        {
            "id": "color-contrast",
            "impact": "serious",
            "description": "Ensures contrast",
            "help": "Elements must have sufficient contrast",
            "helpUrl": "https://dequeuniversity.com/rules/axe/4.12/color-contrast",
            "tags": ["wcag2aa", "wcag143"],
            "nodes": [{"target": ["p"], "html": "<p>x</p>", "failureSummary": "low"}],
        }
    ],
    "incomplete": [
        {
            "id": "color-contrast",
            "impact": "serious",
            "description": "Ensures contrast",
            "help": "Needs review",
            "helpUrl": "https://example.com",
            "tags": ["wcag2aa", "wcag143"],
            "nodes": [{"target": ["span"], "html": "<span>y</span>"}],
        }
    ],
    "passes": [],
}


def _page():
    return builder.build_page_audit(
        target="http://example.test",
        level="AA",
        axe_results=FAKE_AXE,
        govuk_findings=[],
        axe_version="4.12.1",
    )


def test_builder_maps_violations_and_criteria():
    page = _page()
    assert page.ok
    assert page.violation_count == 1
    assert page.needs_review_count == 1
    v = page.violations[0]
    assert v.outcome is Outcome.FAIL
    assert v.wcag_criteria == ["1.4.3"]
    assert v.remediation  # enriched
    assert v.node_count == 1


def test_summary_non_compliant_when_violations_present():
    summary = builder.build_summary([_page()], "AA")
    assert summary.status is ComplianceStatus.NON_COMPLIANT
    assert "1.4.3" in summary.failing_criteria
    assert summary.total_violations == 1


def test_summary_partially_compliant_when_only_needs_review():
    clean = builder.build_page_audit(
        target="t", level="AA",
        axe_results={"violations": [], "incomplete": FAKE_AXE["incomplete"], "passes": []},
        govuk_findings=[],
    )
    summary = builder.build_summary([clean], "AA")
    assert summary.status is ComplianceStatus.PARTIALLY_COMPLIANT


def test_error_page_excluded_from_summary():
    errored = builder.build_page_audit(
        target="bad", level="AA", axe_results={}, govuk_findings=[],
        error="Could not load page",
    )
    summary = builder.build_summary([errored], "AA")
    assert summary.pages_audited == 0
    assert any("could not be audited" in r for r in summary.reasons)


def test_markdown_report_renders():
    md = markdown_report.render_page(_page())
    assert "# Accessibility audit" in md
    assert "color-contrast" in md
    assert "Violations" in md


def test_generate_statement_contains_gds_structure():
    summary = builder.build_summary([_page()], "AA")
    statement = gds_summary.generate_statement(
        summary, service_name="Test Service", organisation="Test Org",
    )
    assert "Accessibility statement for Test Service" in statement
    assert "Compliance status" in statement
    assert "not compliant" in statement.lower()
    # Honesty: must mention manual testing limits and the new 2.2 criteria.
    assert "automated" in statement.lower()
    assert "2.4.11" in statement
