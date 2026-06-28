"""Pydantic data models for audit results.

These are the canonical, serialisable shapes the MCP tools return. The reporting
layer builds them from axe-core's raw output plus the GOV.UK custom checks; the
JSON / Markdown / GDS renderers consume them.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Impact(str, Enum):
    """Severity of a finding, aligned with axe-core's impact levels."""

    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"


class Outcome(str, Enum):
    """What an audit determined about a check.

    AUTOMATED tools can only ever *fail* or *pass* the machine-detectable portion
    of a criterion. NEEDS_REVIEW marks things that require a human (axe
    'incomplete', or WCAG criteria that cannot be automated at all).
    """

    FAIL = "fail"
    PASS = "pass"
    NEEDS_REVIEW = "needs_review"


class ComplianceStatus(str, Enum):
    """The three statuses required by a GOV.UK accessibility statement."""

    COMPLIANT = "compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"


class AffectedNode(BaseModel):
    """A single DOM element implicated in a finding."""

    target: list[str] = Field(default_factory=list, description="CSS selector path to the element")
    html: str = Field("", description="Outer HTML snippet of the element")
    failure_summary: str = Field("", description="axe-core's per-node explanation")


class Finding(BaseModel):
    """One accessibility issue (failure or needs-review item)."""

    id: str = Field(description="Rule id (axe rule id or govuk:<check> id)")
    source: str = Field("axe-core", description="Engine that produced the finding")
    outcome: Outcome
    impact: Impact | None = None
    description: str = Field("", description="What the rule checks")
    help: str = Field("", description="Short guidance on the problem")
    help_url: str = Field("", description="Reference URL (axe / WCAG Understanding)")
    wcag_criteria: list[str] = Field(
        default_factory=list,
        description="WCAG success criteria this finding maps to, e.g. ['1.4.3']",
    )
    wcag_tags: list[str] = Field(default_factory=list, description="Raw axe tags")
    remediation: str = Field("", description="Plain-English fix suggestion")
    technique_url: str = Field("", description="WCAG technique reference")
    govuk_reference: str = Field("", description="Relevant GOV.UK Design System / guidance URL")
    nodes: list[AffectedNode] = Field(default_factory=list)

    @property
    def node_count(self) -> int:
        return len(self.nodes)


class PageAudit(BaseModel):
    """Result of auditing a single page (URL or HTML snippet)."""

    target: str = Field(description="URL audited, or '<html-snippet>'")
    level: str = Field(description="WCAG conformance level tested, e.g. 'AA'")
    wcag_version: str = "2.2"
    axe_version: str = "unknown"
    error: str | None = Field(None, description="Set when the audit could not run")

    violations: list[Finding] = Field(default_factory=list)
    needs_review: list[Finding] = Field(default_factory=list)
    passes: list[Finding] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    @property
    def needs_review_count(self) -> int:
        return len(self.needs_review)

    def impact_breakdown(self) -> dict[str, int]:
        counts = {i.value: 0 for i in Impact}
        for f in self.violations:
            if f.impact is not None:
                counts[f.impact.value] += 1
        return counts


class ComplianceSummary(BaseModel):
    """GDS-style rollup of one or more page audits."""

    status: ComplianceStatus
    level: str = "AA"
    wcag_version: str = "2.2"
    pages_audited: int = 1
    total_violations: int = 0
    total_needs_review: int = 0
    impact_breakdown: dict[str, int] = Field(default_factory=dict)
    failing_criteria: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(
        default_factory=list,
        description="Why this status was assigned (drives the accessibility statement)",
    )


class SiteAudit(BaseModel):
    """Result of crawling and auditing multiple pages."""

    start_url: str
    level: str = "AA"
    wcag_version: str = "2.2"
    pages: list[PageAudit] = Field(default_factory=list)
    summary: ComplianceSummary
