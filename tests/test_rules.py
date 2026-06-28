"""Unit tests for the rules layer (no browser needed)."""

from __future__ import annotations

from accessibility_mcp.rules import govuk_checks, remediation, wcag22
from accessibility_mcp.reporting.models import Outcome


def test_wcag_tag_parsing():
    assert remediation.wcag_criteria_from_tags(["wcag2aa", "wcag143"]) == ["1.4.3"]
    assert remediation.wcag_criteria_from_tags(["wcag1410"]) == ["1.4.10"]
    assert remediation.wcag_criteria_from_tags(["wcag111", "wcag412"]) == ["1.1.1", "4.1.2"]
    # Level tags (letters) are ignored.
    assert remediation.wcag_criteria_from_tags(["wcag2a", "wcag21aa", "best-practice"]) == []


def test_curated_remediation_has_govuk_reference():
    rem = remediation.remediation_for("color-contrast", ["wcag143", "wcag2aa"])
    assert "contrast" in rem["fix"].lower()
    assert rem["govuk_reference"].startswith("https://design-system.service.gov.uk")
    assert rem["wcag_criteria"] == ["1.4.3"]


def test_generic_remediation_fallback_is_never_empty():
    rem = remediation.remediation_for("some-unknown-rule", ["wcag131"])
    assert rem["fix"]
    assert rem["technique_url"]  # derived from the criterion
    assert rem["wcag_criteria"] == ["1.3.1"]


def test_wcag_catalogue_levels_and_new_criteria():
    a_only = wcag22.criteria("A")
    assert all(c.level == "A" for c in a_only)
    aa = wcag22.criteria("AA")
    assert len(aa) > len(a_only)
    # The WCAG 2.2 additions at A/AA must be present and flagged.
    for new in ["2.4.11", "2.5.7", "2.5.8", "3.2.6", "3.3.7", "3.3.8"]:
        assert new in wcag22.NEW_IN_2_2
        assert wcag22.CRITERIA_BY_NUMBER[new].new_in_2_2
    # 4.1.1 Parsing was removed in WCAG 2.2.
    assert "4.1.1" not in wcag22.CRITERIA_BY_NUMBER


def test_understanding_url_built():
    assert wcag22.understanding_url("1.4.3").endswith("contrast-minimum")


def test_govuk_checks_on_failing_markup():
    html = "<html><body><p>hi</p></body></html>"
    findings = {f.id: f for f in govuk_checks.run_govuk_checks(html)}
    assert findings["govuk:skip-link"].outcome is Outcome.FAIL
    assert findings["govuk:main-landmark"].outcome is Outcome.FAIL
    assert findings["govuk:accessibility-statement"].outcome is Outcome.NEEDS_REVIEW


def test_govuk_checks_on_passing_markup():
    html = (
        '<html lang="en"><body>'
        '<a href="#main-content" class="govuk-skip-link">Skip to main content</a>'
        '<main id="main-content"><h1>Title</h1></main>'
        '<footer><a href="/accessibility-statement">Accessibility statement</a></footer>'
        "</body></html>"
    )
    findings = {f.id: f for f in govuk_checks.run_govuk_checks(html)}
    assert findings["govuk:skip-link"].outcome is Outcome.PASS
    assert findings["govuk:main-landmark"].outcome is Outcome.PASS
    assert findings["govuk:accessibility-statement"].outcome is Outcome.PASS
    assert findings["govuk:design-system"].outcome is Outcome.PASS
