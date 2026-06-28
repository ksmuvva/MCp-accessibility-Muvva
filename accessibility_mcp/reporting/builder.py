"""Build :class:`PageAudit` objects from raw axe-core output and GOV.UK checks.

This is the bridge between the engine/rules layers and the renderers. It:
  * converts each axe violation / incomplete / pass into a :class:`Finding`,
  * enriches it with remediation guidance and WCAG criteria,
  * folds in the GOV.UK custom-check findings,
  * and computes the GDS-style :class:`ComplianceSummary`.
"""

from __future__ import annotations

from accessibility_mcp.reporting.models import (
    AffectedNode,
    ComplianceStatus,
    ComplianceSummary,
    Finding,
    Impact,
    Outcome,
    PageAudit,
)
from accessibility_mcp.rules import remediation, wcag22


def _impact(value: str | None) -> Impact | None:
    if not value:
        return None
    try:
        return Impact(value)
    except ValueError:
        return None


def _nodes(raw_nodes: list[dict]) -> list[AffectedNode]:
    nodes: list[AffectedNode] = []
    for n in raw_nodes:
        target = n.get("target", [])
        # axe targets can be nested lists for iframes; flatten to strings.
        flat = [t if isinstance(t, str) else " ".join(map(str, t)) for t in target]
        nodes.append(
            AffectedNode(
                target=flat,
                html=(n.get("html") or "")[:600],
                failure_summary=n.get("failureSummary") or "",
            )
        )
    return nodes


def _finding_from_axe(rule: dict, outcome: Outcome) -> Finding:
    rule_id = rule.get("id", "unknown")
    tags = rule.get("tags", [])
    rem = remediation.remediation_for(rule_id, tags)
    return Finding(
        id=rule_id,
        source="axe-core",
        outcome=outcome,
        impact=_impact(rule.get("impact")),
        description=rule.get("description", ""),
        help=rule.get("help", ""),
        help_url=rule.get("helpUrl", ""),
        wcag_criteria=rem["wcag_criteria"],
        wcag_tags=tags,
        remediation=rem["fix"],
        technique_url=rem["technique_url"],
        govuk_reference=rem["govuk_reference"],
        nodes=_nodes(rule.get("nodes", [])),
    )


def build_page_audit(
    *,
    target: str,
    level: str,
    axe_results: dict,
    govuk_findings: list[Finding],
    axe_version: str = "unknown",
    error: str | None = None,
) -> PageAudit:
    """Assemble a PageAudit from axe output + GOV.UK findings."""
    if error is not None:
        return PageAudit(target=target, level=level, axe_version=axe_version, error=error)

    violations = [_finding_from_axe(r, Outcome.FAIL) for r in axe_results.get("violations", [])]
    needs_review = [_finding_from_axe(r, Outcome.NEEDS_REVIEW) for r in axe_results.get("incomplete", [])]
    passes = [_finding_from_axe(r, Outcome.PASS) for r in axe_results.get("passes", [])]

    # Fold in GOV.UK custom checks by outcome.
    for f in govuk_findings:
        if f.outcome is Outcome.FAIL:
            violations.append(f)
        elif f.outcome is Outcome.NEEDS_REVIEW:
            needs_review.append(f)
        else:
            passes.append(f)

    return PageAudit(
        target=target,
        level=level,
        axe_version=axe_version,
        violations=violations,
        needs_review=needs_review,
        passes=passes,
    )


def _collect_failing_criteria(pages: list[PageAudit]) -> list[str]:
    criteria: set[str] = set()
    for p in pages:
        for f in p.violations:
            criteria.update(f.wcag_criteria)
    return sorted(criteria, key=lambda c: [int(x) for x in c.split(".")])


def build_summary(pages: list[PageAudit], level: str) -> ComplianceSummary:
    """Compute the GDS-style compliance status across one or more pages.

    Status logic (deliberately conservative — this underpins a legal statement):
      * NON_COMPLIANT  if there are any automated WCAG failures.
      * PARTIALLY_COMPLIANT if there are no automated failures but items need
        manual review (axe 'incomplete', GOV.UK checks, or the inherent fact that
        many AA criteria cannot be automated).
      * COMPLIANT only when nothing failed AND nothing needs review — which in
        practice still requires a manual audit to claim; we say so in 'reasons'.
    """
    ok_pages = [p for p in pages if p.ok]
    total_violations = sum(p.violation_count for p in ok_pages)
    total_needs_review = sum(p.needs_review_count for p in ok_pages)

    impact_breakdown: dict[str, int] = {i.value: 0 for i in Impact}
    for p in ok_pages:
        for k, v in p.impact_breakdown().items():
            impact_breakdown[k] += v

    failing_criteria = _collect_failing_criteria(ok_pages)
    reasons: list[str] = []

    errored = [p for p in pages if not p.ok]
    if errored:
        reasons.append(f"{len(errored)} page(s) could not be audited and were excluded.")

    if total_violations > 0:
        status = ComplianceStatus.NON_COMPLIANT
        reasons.append(
            f"{total_violations} automated WCAG {level} failure(s) detected across "
            f"{len(ok_pages)} page(s), affecting criteria: {', '.join(failing_criteria) or 'n/a'}."
        )
    elif total_needs_review > 0:
        status = ComplianceStatus.PARTIALLY_COMPLIANT
        reasons.append(
            f"No automated failures, but {total_needs_review} item(s) need manual review."
        )
    else:
        status = ComplianceStatus.PARTIALLY_COMPLIANT
        reasons.append(
            "No automated failures detected. Automated testing covers only part of "
            "WCAG 2.2 AA, so a manual audit is still required to claim full compliance."
        )

    # Always remind that non-automatable AA criteria remain unverified.
    manual = wcag22.manual_criteria(level)
    reasons.append(
        f"{len(manual)} WCAG {level} criteria cannot be fully automated and require "
        "manual assessment (e.g. keyboard operation, focus order, captions, and the "
        "new WCAG 2.2 criteria 2.4.11, 2.5.7, 3.3.8)."
    )

    return ComplianceSummary(
        status=status,
        level=level,
        pages_audited=len(ok_pages),
        total_violations=total_violations,
        total_needs_review=total_needs_review,
        impact_breakdown=impact_breakdown,
        failing_criteria=failing_criteria,
        reasons=reasons,
    )
