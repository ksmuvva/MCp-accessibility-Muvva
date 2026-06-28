"""GOV.UK / GDS-specific accessibility checks.

axe-core covers the generic WCAG machine-detectable rules; these checks add
expectations specific to UK public sector services that axe does not know about:

  * an accessibility statement is linked (a legal requirement for public sector
    bodies under the 2018 Regulations);
  * a "Skip to main content" skip link is present (GOV.UK page template default);
  * a single <main> landmark exists as the skip-link target;
  * whether the page appears to use the GOV.UK Design System (govuk-frontend),
    which is informational context for reviewers.

Each check returns a :class:`~accessibility_mcp.reporting.models.Finding` with
source "govuk". We use NEEDS_REVIEW (not FAIL) when absence is suggestive but not
conclusive — e.g. the statement could be linked from a global footer we did not
fetch — to stay honest about what automation can prove.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from accessibility_mcp.reporting.models import AffectedNode, Finding, Impact, Outcome

GOVUK_REGS = "https://www.gov.uk/guidance/accessibility-requirements-for-public-sector-websites-and-apps"
GOVUK_STATEMENT_GUIDE = "https://www.gov.uk/guidance/make-your-website-or-app-accessible-and-publish-an-accessibility-statement"
GOVUK_DESIGN_SYSTEM = "https://design-system.service.gov.uk"

_ACCESSIBILITY_LINK_RE = re.compile(r"accessibility", re.IGNORECASE)
_SKIP_LINK_TEXT_RE = re.compile(r"skip to (main )?content", re.IGNORECASE)


def _finding(
    check_id: str,
    outcome: Outcome,
    *,
    help_text: str,
    remediation: str,
    impact: Impact | None = None,
    wcag: list[str] | None = None,
    govuk_ref: str = GOVUK_REGS,
    nodes: list[AffectedNode] | None = None,
) -> Finding:
    return Finding(
        id=check_id,
        source="govuk",
        outcome=outcome,
        impact=impact,
        description=help_text,
        help=help_text,
        help_url=govuk_ref,
        wcag_criteria=wcag or [],
        remediation=remediation,
        govuk_reference=govuk_ref,
        nodes=nodes or [],
    )


def _check_accessibility_statement(soup: BeautifulSoup) -> Finding:
    links = soup.find_all("a", href=True)
    for a in links:
        text = a.get_text(" ", strip=True)
        href = a["href"]
        if _ACCESSIBILITY_LINK_RE.search(text) or _ACCESSIBILITY_LINK_RE.search(href):
            return _finding(
                "govuk:accessibility-statement",
                Outcome.PASS,
                help_text="An accessibility statement link was found on the page.",
                remediation="Verify the linked statement is up to date and lists known "
                "issues and the compliance status, as required.",
                govuk_ref=GOVUK_STATEMENT_GUIDE,
                nodes=[AffectedNode(target=["a"], html=str(a)[:300])],
            )
    return _finding(
        "govuk:accessibility-statement",
        Outcome.NEEDS_REVIEW,
        help_text="No accessibility statement link was detected on this page.",
        remediation="Public sector bodies must publish and link to an accessibility "
        "statement. Add a clearly labelled 'Accessibility statement' link (commonly "
        "in the footer) and ensure it meets the GDS model wording.",
        impact=Impact.SERIOUS,
        govuk_ref=GOVUK_STATEMENT_GUIDE,
    )


def _check_skip_link(soup: BeautifulSoup) -> Finding:
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        classes = " ".join(a.get("class") or []).lower()
        is_skip = _SKIP_LINK_TEXT_RE.search(text) or (
            a["href"].startswith("#") and "skip-link" in classes
        )
        if is_skip:
            return _finding(
                "govuk:skip-link",
                Outcome.PASS,
                help_text="A 'Skip to main content' link was found.",
                remediation="Ensure the skip link targets the main content container "
                "and is the first focusable element.",
                wcag=["2.4.1"],
                govuk_ref=f"{GOVUK_DESIGN_SYSTEM}/components/skip-link/",
                nodes=[AffectedNode(target=["a"], html=str(a)[:300])],
            )
    return _finding(
        "govuk:skip-link",
        Outcome.FAIL,
        help_text="No 'Skip to main content' skip link was found.",
        remediation="Add a skip link as the first focusable element, as provided by "
        "the GOV.UK page template, so keyboard users can bypass repeated navigation.",
        impact=Impact.MODERATE,
        wcag=["2.4.1"],
        govuk_ref=f"{GOVUK_DESIGN_SYSTEM}/components/skip-link/",
    )


def _check_main_landmark(soup: BeautifulSoup) -> Finding:
    mains = soup.find_all("main")
    if len(mains) == 1:
        return _finding(
            "govuk:main-landmark",
            Outcome.PASS,
            help_text="Exactly one <main> landmark was found.",
            remediation="Good — keep a single <main> as the skip-link target.",
            wcag=["1.3.1"],
        )
    if len(mains) == 0:
        return _finding(
            "govuk:main-landmark",
            Outcome.FAIL,
            help_text="No <main> landmark was found.",
            remediation="Wrap the primary page content in a single <main> element "
            "(the GOV.UK template uses <main id=\"main-content\">).",
            impact=Impact.MODERATE,
            wcag=["1.3.1"],
        )
    return _finding(
        "govuk:main-landmark",
        Outcome.FAIL,
        help_text=f"{len(mains)} <main> landmarks were found; there should be one.",
        remediation="Use exactly one <main> landmark per page.",
        impact=Impact.MODERATE,
        wcag=["1.3.1"],
    )


def _check_design_system(soup: BeautifulSoup) -> Finding:
    uses_govuk = bool(soup.select('[class*="govuk-"]'))
    if uses_govuk:
        return _finding(
            "govuk:design-system",
            Outcome.PASS,
            help_text="The page appears to use the GOV.UK Design System (govuk-* classes).",
            remediation="Keep components up to date; the Design System ships accessible "
            "patterns tested against WCAG 2.2 AA.",
            govuk_ref=GOVUK_DESIGN_SYSTEM,
        )
    return _finding(
        "govuk:design-system",
        Outcome.NEEDS_REVIEW,
        help_text="No GOV.UK Design System classes detected (informational).",
        remediation="Using the GOV.UK Design System is recommended for public sector "
        "services — its components are built and tested for accessibility.",
        govuk_ref=GOVUK_DESIGN_SYSTEM,
    )


def run_govuk_checks(html: str) -> list[Finding]:
    """Run all GOV.UK-specific checks against the page HTML."""
    soup = BeautifulSoup(html or "", "html.parser")
    return [
        _check_accessibility_statement(soup),
        _check_skip_link(soup),
        _check_main_landmark(soup),
        _check_design_system(soup),
    ]
