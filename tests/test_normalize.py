"""Unit tests for engine output normalisation (no browser needed)."""

from __future__ import annotations

from accessibility_mcp.reporting.models import Outcome
from accessibility_mcp.rules import normalize


def test_htmlcs_criterion_parsing():
    assert normalize._criterion_from_htmlcs(
        "WCAG2AA.Principle1.Guideline1_1.1_1_1.H37"
    ) == ["1.1.1"]
    assert normalize._criterion_from_htmlcs(
        "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail"
    ) == ["1.4.3"]


def test_normalize_pa11y_htmlcs_and_axe():
    payload = {
        "issues": [
            {
                "code": "WCAG2AA.Principle1.Guideline1_1.1_1_1.H37",
                "type": "error",
                "message": "Img missing alt",
                "selector": "html > body > img",
                "context": "<img src='x'>",
                "runner": "htmlcs",
            },
            {
                "code": "color-contrast",
                "type": "warning",
                "message": "Contrast",
                "selector": "p",
                "context": "<p>x</p>",
                "runner": "axe",
            },
        ]
    }
    findings = normalize.normalize_pa11y(payload)
    assert findings[0].source == "pa11y"
    assert findings[0].outcome is Outcome.FAIL
    assert findings[0].wcag_criteria == ["1.1.1"]
    # axe runner code maps to the axe rule's criteria + curated remediation.
    assert findings[1].outcome is Outcome.NEEDS_REVIEW
    assert findings[1].wcag_criteria == ["1.4.3"]
    assert "contrast" in findings[1].remediation.lower()


def test_normalize_lighthouse_maps_axe_ids():
    payload = {
        "score": 0.5,
        "audits": [
            {
                "id": "image-alt",
                "title": "Image elements do not have [alt]",
                "description": "...",
                "score": 0,
                "items": [{"selector": "img", "snippet": "<img>"}],
            }
        ],
    }
    findings = normalize.normalize_lighthouse(payload)
    assert findings[0].source == "lighthouse"
    assert findings[0].outcome is Outcome.FAIL
    assert findings[0].wcag_criteria == ["1.1.1"]
    assert findings[0].node_count == 1


def test_normalize_ibm_levels():
    payload = {
        "results": [
            {"ruleId": "img_alt_valid", "message": "alt", "level": "FAIL", "value": ["VIOLATION", "FAIL"], "path": "/html/body/img"},
            {"ruleId": "x", "message": "maybe", "level": "POTENTIAL", "value": ["RECOMMENDATION", "POTENTIAL"]},
        ]
    }
    findings = normalize.normalize_ibm(payload)
    assert findings[0].outcome is Outcome.FAIL
    assert findings[1].outcome is Outcome.NEEDS_REVIEW
    assert all(f.source == "ibm" for f in findings)


def test_normalize_unknown_engine_is_empty():
    assert normalize.normalize_engine("nope", {"issues": []}) == []
