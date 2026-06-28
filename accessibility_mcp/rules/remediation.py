"""Remediation guidance and WCAG-criterion mapping for findings.

axe-core already carries a ``helpUrl`` and rule tags; this module enriches each
finding with (a) the WCAG success criteria it maps to (parsed from axe tags),
(b) a plain-English fix, and (c) a relevant GOV.UK Design System / guidance link
where one applies. Rules not in the curated table still get criteria + a WCAG
Understanding link via the generic fallback, so guidance is never empty.
"""

from __future__ import annotations

import re

from accessibility_mcp.rules import wcag22

# axe encodes WCAG criteria as tags like "wcag143" (=> 1.4.3) or "wcag1410"
# (=> 1.4.10). Level tags (wcag2aa, wcag21a, wcag22aa, best-practice) contain
# letters and are skipped by this digits-only pattern.
_WCAG_TAG_RE = re.compile(r"^wcag(\d)(\d)(\d{1,2})$")

GOVUK_DESIGN_SYSTEM = "https://design-system.service.gov.uk"
GOVUK_A11Y_GUIDE = "https://www.gov.uk/service-manual/helping-people-to-use-your-service"


def wcag_criteria_from_tags(tags: list[str]) -> list[str]:
    """Convert axe rule tags into dotted WCAG criterion numbers, e.g. '1.4.3'."""
    out: list[str] = []
    for tag in tags:
        m = _WCAG_TAG_RE.match(tag)
        if m:
            out.append(f"{m.group(1)}.{m.group(2)}.{int(m.group(3))}")
    # Stable, de-duplicated.
    seen: set[str] = set()
    return [c for c in out if not (c in seen or seen.add(c))]


# Curated remediation for the axe rules GDS reviewers see most often.
# Keyed by axe rule id. technique_url points at a WCAG technique or Understanding
# page; govuk points at the most relevant Design System component / guidance.
_REMEDIATION: dict[str, dict[str, str]] = {
    "color-contrast": {
        "fix": "Increase the contrast ratio between text and its background to at "
        "least 4.5:1 (3:1 for large text ≥ 18.66px bold or 24px). Use the GOV.UK "
        "colour palette, which is designed to meet AA contrast.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/general/G18",
        "govuk": f"{GOVUK_DESIGN_SYSTEM}/styles/colour/",
    },
    "image-alt": {
        "fix": "Add a meaningful alt attribute to the image describing its purpose, "
        "or alt=\"\" if it is purely decorative so assistive tech can ignore it.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/html/H37",
        "govuk": f"{GOVUK_DESIGN_SYSTEM}/styles/images/",
    },
    "label": {
        "fix": "Associate a visible <label> with the form control using for/id, or "
        "wrap the control in the label. Avoid placeholder-only labelling.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/html/H44",
        "govuk": f"{GOVUK_DESIGN_SYSTEM}/components/text-input/",
    },
    "link-name": {
        "fix": "Give the link discernible text. Avoid 'click here'/'read more'; make "
        "the link text describe its destination.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/general/G91",
        "govuk": f"{GOVUK_DESIGN_SYSTEM}/styles/links/",
    },
    "button-name": {
        "fix": "Provide an accessible name for the button via its text content, "
        "aria-label, or aria-labelledby.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/general/G115",
        "govuk": f"{GOVUK_DESIGN_SYSTEM}/components/button/",
    },
    "html-has-lang": {
        "fix": "Add a lang attribute to the <html> element (e.g. lang=\"en\") so "
        "screen readers use the correct pronunciation.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/html/H57",
        "govuk": GOVUK_A11Y_GUIDE,
    },
    "html-lang-valid": {
        "fix": "Use a valid BCP 47 language tag in the <html> lang attribute.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/html/H57",
        "govuk": GOVUK_A11Y_GUIDE,
    },
    "document-title": {
        "fix": "Add a non-empty, descriptive <title> that identifies the page and "
        "the service.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/general/G88",
        "govuk": GOVUK_A11Y_GUIDE,
    },
    "heading-order": {
        "fix": "Use headings in a logical order without skipping levels (h1 then h2, "
        "etc.) so the page structure is conveyed correctly.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/general/G141",
        "govuk": f"{GOVUK_DESIGN_SYSTEM}/styles/typography/",
    },
    "empty-heading": {
        "fix": "Remove empty headings or add meaningful text content to them.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/general/G130",
        "govuk": f"{GOVUK_DESIGN_SYSTEM}/styles/typography/",
    },
    "list": {
        "fix": "Ensure <ul>/<ol> contain only <li> (and script-supporting) children "
        "so list semantics are valid.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/html/H48",
        "govuk": GOVUK_A11Y_GUIDE,
    },
    "region": {
        "fix": "Place all meaningful content inside landmark regions (header, nav, "
        "main, footer) so users can navigate by landmark.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA11",
        "govuk": GOVUK_A11Y_GUIDE,
    },
    "landmark-one-main": {
        "fix": "Include exactly one <main> landmark so assistive tech users can jump "
        "straight to the primary content.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA11",
        "govuk": GOVUK_A11Y_GUIDE,
    },
    "bypass": {
        "fix": "Provide a 'Skip to main content' link as the first focusable element, "
        "as the GOV.UK page template does by default.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/general/G1",
        "govuk": f"{GOVUK_DESIGN_SYSTEM}/components/skip-link/",
    },
    "aria-required-attr": {
        "fix": "Add the required ARIA attributes for the element's role, or use a "
        "native HTML element that conveys the same semantics.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA5",
        "govuk": GOVUK_A11Y_GUIDE,
    },
    "frame-title": {
        "fix": "Give every <iframe> a title attribute describing its content.",
        "technique_url": "https://www.w3.org/WAI/WCAG22/Techniques/html/H64",
        "govuk": GOVUK_A11Y_GUIDE,
    },
    "target-size": {
        "fix": "Make interactive targets at least 24x24 CSS pixels, or leave enough "
        "spacing around smaller targets (WCAG 2.2 SC 2.5.8).",
        "technique_url": f"{wcag22.UNDERSTANDING_BASE}target-size-minimum",
        "govuk": f"{GOVUK_DESIGN_SYSTEM}/components/button/",
    },
}


def remediation_for(rule_id: str, tags: list[str]) -> dict[str, str]:
    """Return {'fix', 'technique_url', 'govuk_reference', 'wcag_criteria'} for a rule.

    Uses the curated table when available; otherwise derives a generic fix and a
    WCAG Understanding link from the rule's WCAG criteria so guidance is never blank.
    """
    criteria = wcag_criteria_from_tags(tags)
    curated = _REMEDIATION.get(rule_id)
    if curated:
        return {
            "fix": curated["fix"],
            "technique_url": curated.get("technique_url", ""),
            "govuk_reference": curated.get("govuk", GOVUK_A11Y_GUIDE),
            "wcag_criteria": criteria,
        }

    # Generic fallback.
    technique = wcag22.understanding_url(criteria[0]) if criteria else ""
    if criteria:
        names = ", ".join(
            f"{c} {wcag22.CRITERIA_BY_NUMBER[c].name}"
            for c in criteria
            if c in wcag22.CRITERIA_BY_NUMBER
        )
        fix = (
            f"Review against WCAG 2.2 success criteria: {names or ', '.join(criteria)}. "
            "Follow the linked W3C Understanding guidance to resolve the issue."
        )
    else:
        fix = "Review the linked guidance and resolve the reported issue."
    return {
        "fix": fix,
        "technique_url": technique,
        "govuk_reference": GOVUK_A11Y_GUIDE,
        "wcag_criteria": criteria,
    }
