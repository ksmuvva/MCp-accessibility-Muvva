"""Integration tests that drive a real headless Chromium via Playwright.

These exercise the full audit pipeline (browser -> axe-core -> GOV.UK checks ->
report) on local HTML fixtures, so no network access is required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from accessibility_mcp import audit
from accessibility_mcp.reporting import gds_summary
from accessibility_mcp.reporting.models import ComplianceStatus

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_failing_page_reports_violations():
    html = (FIXTURES / "failing.html").read_text()
    result = await audit.audit_html(html, level="AA")
    assert result.ok
    assert result.violation_count > 0
    rule_ids = {v.id for v in result.violations}
    # axe should catch these classic failures in the fixture.
    assert "image-alt" in rule_ids
    assert "html-has-lang" in rule_ids
    # GOV.UK checks should flag the missing skip link / main landmark.
    assert "govuk:skip-link" in rule_ids
    summary = gds_summary.summary_from(result)
    assert summary.status is ComplianceStatus.NON_COMPLIANT


@pytest.mark.asyncio
async def test_govuk_passing_page_has_no_govuk_check_failures():
    html = (FIXTURES / "govuk_passing.html").read_text()
    result = await audit.audit_html(html, level="AA")
    assert result.ok
    govuk_failures = [v for v in result.violations if v.source == "govuk"]
    assert govuk_failures == []
    # The Design System + skip link + main + statement should all pass.
    passed_ids = {p.id for p in result.passes}
    assert "govuk:skip-link" in passed_ids
    assert "govuk:main-landmark" in passed_ids
    assert "govuk:accessibility-statement" in passed_ids
