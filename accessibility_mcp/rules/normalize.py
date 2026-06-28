"""Normalise pa11y / Lighthouse / IBM engine output into our Finding model.

Each engine reports issues in its own shape and vocabulary. This module maps them
to a common :class:`~accessibility_mcp.reporting.models.Finding`, deriving WCAG
success criteria where possible so findings from different engines can be compared
and deduplicated alongside axe-core results.
"""

from __future__ import annotations

import re

from accessibility_mcp.reporting.models import AffectedNode, Finding, Impact, Outcome
from accessibility_mcp.rules import axe_rules, remediation, wcag22

# HTML_CodeSniffer codes look like:
#   WCAG2AA.Principle1.Guideline1_1.1_1_1.H37
# The success criterion is the "1_1_1" segment (three underscore-separated numbers).
_HTMLCS_SC_RE = re.compile(r"\b(\d+)_(\d+)_(\d+)\b")


def _criterion_from_htmlcs(code: str) -> list[str]:
    out: list[str] = []
    for m in _HTMLCS_SC_RE.finditer(code):
        out.append(f"{int(m.group(1))}.{int(m.group(2))}.{int(m.group(3))}")
    # De-dupe, preserve order.
    seen: set[str] = set()
    return [c for c in out if not (c in seen or seen.add(c))]


def _understanding(criteria: list[str]) -> str:
    return wcag22.understanding_url(criteria[0]) if criteria else ""


# --------------------------------------------------------------------------- #
# pa11y (HTML_CodeSniffer + axe runners)
# --------------------------------------------------------------------------- #


def normalize_pa11y(payload: dict) -> list[Finding]:
    findings: list[Finding] = []
    for issue in payload.get("issues", []):
        code = issue.get("code", "")
        runner = issue.get("runner", "htmlcs")
        itype = issue.get("type", "error")
        outcome = Outcome.FAIL if itype == "error" else Outcome.NEEDS_REVIEW
        impact = Impact.SERIOUS if itype == "error" else Impact.MODERATE

        if runner == "axe":
            # pa11y's axe runner uses axe rule ids as the code.
            rule = axe_rules.get_rule(code)
            criteria = rule.wcag_criteria if rule else []
            rem = remediation.remediation_for(code, list(rule.tags) if rule else [])
            help_url = rule.help_url if rule else ""
            remediation_text = rem["fix"]
            technique = rem["technique_url"]
            govuk = rem["govuk_reference"]
        else:
            criteria = _criterion_from_htmlcs(code)
            help_url = _understanding(criteria)
            remediation_text = (
                "Resolve per the WCAG technique referenced in the code "
                f"({code.split('.')[-1] if '.' in code else code}). See the linked guidance."
            )
            technique = _understanding(criteria)
            govuk = remediation.GOVUK_A11Y_GUIDE

        findings.append(
            Finding(
                id=code,
                source="pa11y",
                outcome=outcome,
                impact=impact,
                description=issue.get("message", ""),
                help=issue.get("message", ""),
                help_url=help_url,
                wcag_criteria=criteria,
                remediation=remediation_text,
                technique_url=technique,
                govuk_reference=govuk,
                nodes=[
                    AffectedNode(
                        target=[issue["selector"]] if issue.get("selector") else [],
                        html=(issue.get("context") or "")[:600],
                    )
                ],
            )
        )
    return findings


# --------------------------------------------------------------------------- #
# Lighthouse (accessibility category — uses axe under the hood)
# --------------------------------------------------------------------------- #


def normalize_lighthouse(payload: dict) -> list[Finding]:
    findings: list[Finding] = []
    for audit in payload.get("audits", []):
        audit_id = audit.get("id", "")
        # Lighthouse a11y audit ids correspond to axe rule ids.
        rule = axe_rules.get_rule(audit_id)
        criteria = rule.wcag_criteria if rule else []
        rem = remediation.remediation_for(audit_id, list(rule.tags) if rule else [])
        nodes = [
            AffectedNode(
                target=[it["selector"]] if it.get("selector") else [],
                html=(it.get("snippet") or "")[:600],
            )
            for it in audit.get("items", [])
        ]
        findings.append(
            Finding(
                id=audit_id,
                source="lighthouse",
                outcome=Outcome.FAIL,
                impact=Impact.SERIOUS,
                description=audit.get("title", ""),
                help=audit.get("description", ""),
                help_url=rule.help_url if rule else "",
                wcag_criteria=criteria,
                remediation=rem["fix"],
                technique_url=rem["technique_url"],
                govuk_reference=rem["govuk_reference"],
                nodes=nodes,
            )
        )
    return findings


# --------------------------------------------------------------------------- #
# IBM Equal Access (accessibility-checker)
# --------------------------------------------------------------------------- #


def normalize_ibm(payload: dict) -> list[Finding]:
    findings: list[Finding] = []
    for r in payload.get("results", []):
        level = r.get("level", "FAIL")
        outcome = Outcome.FAIL if level == "FAIL" else Outcome.NEEDS_REVIEW
        impact = Impact.SERIOUS if level == "FAIL" else Impact.MODERATE
        path = r.get("path") or ""
        findings.append(
            Finding(
                id=r.get("ruleId", "ibm-rule"),
                source="ibm",
                outcome=outcome,
                impact=impact,
                description=r.get("message", ""),
                help=r.get("help", "") or r.get("message", ""),
                help_url="",
                wcag_criteria=[],  # IBM ruleIds do not map 1:1 to WCAG numbers.
                remediation="Review against IBM Equal Access guidance for this rule.",
                nodes=[AffectedNode(target=[path] if path else [], html=(r.get("snippet") or "")[:600])],
            )
        )
    return findings


_NORMALIZERS = {
    "pa11y": normalize_pa11y,
    "lighthouse": normalize_lighthouse,
    "ibm": normalize_ibm,
}


def normalize_engine(name: str, payload: dict) -> list[Finding]:
    """Normalise a single engine's payload. Unknown engines yield no findings."""
    fn = _NORMALIZERS.get(name)
    return fn(payload) if fn else []
