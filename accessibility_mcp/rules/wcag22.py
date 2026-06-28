"""WCAG 2.2 success-criteria catalogue (levels A and AA).

GOV.UK / public sector bodies must meet WCAG 2.2 level AA. This module is the
authoritative list of the criteria the server reasons about: which can be
meaningfully automated (axe-core), which are partially automatable, and which
require human review. It powers ``list_wcag_rules`` and lets the GDS summary flag
non-automatable AA criteria as "needs manual review" rather than silently passing.

``automation`` values:
  - "full"    : automated tools reliably detect failures.
  - "partial" : tools catch some failures but a human must confirm.
  - "manual"  : not machine-detectable; requires human assessment.

WCAG 2.2 removed 4.1.1 Parsing and added 9 new criteria (6 at A/AA), flagged below.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

UNDERSTANDING_BASE = "https://www.w3.org/WAI/WCAG22/Understanding/"

# Map criterion number -> URL slug used by the W3C Understanding pages.
_SLUGS: dict[str, str] = {
    "1.1.1": "non-text-content",
    "1.2.1": "audio-only-and-video-only-prerecorded",
    "1.2.2": "captions-prerecorded",
    "1.2.3": "audio-description-or-media-alternative-prerecorded",
    "1.2.4": "captions-live",
    "1.2.5": "audio-description-prerecorded",
    "1.3.1": "info-and-relationships",
    "1.3.2": "meaningful-sequence",
    "1.3.3": "sensory-characteristics",
    "1.3.4": "orientation",
    "1.3.5": "identify-input-purpose",
    "1.4.1": "use-of-color",
    "1.4.2": "audio-control",
    "1.4.3": "contrast-minimum",
    "1.4.4": "resize-text",
    "1.4.5": "images-of-text",
    "1.4.10": "reflow",
    "1.4.11": "non-text-contrast",
    "1.4.12": "text-spacing",
    "1.4.13": "content-on-hover-or-focus",
    "2.1.1": "keyboard",
    "2.1.2": "no-keyboard-trap",
    "2.1.4": "character-key-shortcuts",
    "2.2.1": "timing-adjustable",
    "2.2.2": "pause-stop-hide",
    "2.3.1": "three-flashes-or-below-threshold",
    "2.4.1": "bypass-blocks",
    "2.4.2": "page-titled",
    "2.4.3": "focus-order",
    "2.4.4": "link-purpose-in-context",
    "2.4.5": "multiple-ways",
    "2.4.6": "headings-and-labels",
    "2.4.7": "focus-visible",
    "2.4.11": "focus-not-obscured-minimum",
    "2.5.1": "pointer-gestures",
    "2.5.2": "pointer-cancellation",
    "2.5.3": "label-in-name",
    "2.5.4": "motion-actuation",
    "2.5.7": "dragging-movements",
    "2.5.8": "target-size-minimum",
    "3.1.1": "language-of-page",
    "3.1.2": "language-of-parts",
    "3.2.1": "on-focus",
    "3.2.2": "on-input",
    "3.2.3": "consistent-navigation",
    "3.2.4": "consistent-identification",
    "3.2.6": "consistent-help",
    "3.3.1": "error-identification",
    "3.3.2": "labels-or-instructions",
    "3.3.3": "error-suggestion",
    "3.3.4": "error-prevention-legal-financial-data",
    "3.3.7": "redundant-entry",
    "3.3.8": "accessible-authentication-minimum",
    "4.1.2": "name-role-value",
    "4.1.3": "status-messages",
}


@dataclass(frozen=True)
class Criterion:
    number: str
    name: str
    level: str  # "A" or "AA"
    automation: str  # "full" | "partial" | "manual"
    new_in_2_2: bool = False

    @property
    def understanding_url(self) -> str:
        slug = _SLUGS.get(self.number, "")
        return f"{UNDERSTANDING_BASE}{slug}" if slug else UNDERSTANDING_BASE

    def to_dict(self) -> dict:
        d = asdict(self)
        d["understanding_url"] = self.understanding_url
        return d


# (number, name, level, automation, new_in_2_2)
_CRITERIA: list[Criterion] = [
    Criterion("1.1.1", "Non-text Content", "A", "partial"),
    Criterion("1.2.1", "Audio-only and Video-only (Prerecorded)", "A", "manual"),
    Criterion("1.2.2", "Captions (Prerecorded)", "A", "manual"),
    Criterion("1.2.3", "Audio Description or Media Alternative (Prerecorded)", "A", "manual"),
    Criterion("1.2.4", "Captions (Live)", "AA", "manual"),
    Criterion("1.2.5", "Audio Description (Prerecorded)", "AA", "manual"),
    Criterion("1.3.1", "Info and Relationships", "A", "partial"),
    Criterion("1.3.2", "Meaningful Sequence", "A", "partial"),
    Criterion("1.3.3", "Sensory Characteristics", "A", "manual"),
    Criterion("1.3.4", "Orientation", "AA", "partial"),
    Criterion("1.3.5", "Identify Input Purpose", "AA", "partial"),
    Criterion("1.4.1", "Use of Color", "A", "manual"),
    Criterion("1.4.2", "Audio Control", "A", "partial"),
    Criterion("1.4.3", "Contrast (Minimum)", "AA", "full"),
    Criterion("1.4.4", "Resize Text", "AA", "manual"),
    Criterion("1.4.5", "Images of Text", "AA", "manual"),
    Criterion("1.4.10", "Reflow", "AA", "manual"),
    Criterion("1.4.11", "Non-text Contrast", "AA", "partial"),
    Criterion("1.4.12", "Text Spacing", "AA", "manual"),
    Criterion("1.4.13", "Content on Hover or Focus", "AA", "manual"),
    Criterion("2.1.1", "Keyboard", "A", "partial"),
    Criterion("2.1.2", "No Keyboard Trap", "A", "manual"),
    Criterion("2.1.4", "Character Key Shortcuts", "A", "manual"),
    Criterion("2.2.1", "Timing Adjustable", "A", "manual"),
    Criterion("2.2.2", "Pause, Stop, Hide", "A", "manual"),
    Criterion("2.3.1", "Three Flashes or Below Threshold", "A", "manual"),
    Criterion("2.4.1", "Bypass Blocks", "A", "full"),
    Criterion("2.4.2", "Page Titled", "A", "full"),
    Criterion("2.4.3", "Focus Order", "A", "manual"),
    Criterion("2.4.4", "Link Purpose (In Context)", "A", "partial"),
    Criterion("2.4.5", "Multiple Ways", "AA", "manual"),
    Criterion("2.4.6", "Headings and Labels", "AA", "partial"),
    Criterion("2.4.7", "Focus Visible", "AA", "partial"),
    Criterion("2.4.11", "Focus Not Obscured (Minimum)", "AA", "manual", new_in_2_2=True),
    Criterion("2.5.1", "Pointer Gestures", "A", "manual"),
    Criterion("2.5.2", "Pointer Cancellation", "A", "manual"),
    Criterion("2.5.3", "Label in Name", "A", "partial"),
    Criterion("2.5.4", "Motion Actuation", "A", "manual"),
    Criterion("2.5.7", "Dragging Movements", "AA", "manual", new_in_2_2=True),
    Criterion("2.5.8", "Target Size (Minimum)", "AA", "partial", new_in_2_2=True),
    Criterion("3.1.1", "Language of Page", "A", "full"),
    Criterion("3.1.2", "Language of Parts", "AA", "partial"),
    Criterion("3.2.1", "On Focus", "A", "manual"),
    Criterion("3.2.2", "On Input", "A", "manual"),
    Criterion("3.2.3", "Consistent Navigation", "AA", "manual"),
    Criterion("3.2.4", "Consistent Identification", "AA", "manual"),
    Criterion("3.2.6", "Consistent Help", "A", "manual", new_in_2_2=True),
    Criterion("3.3.1", "Error Identification", "A", "partial"),
    Criterion("3.3.2", "Labels or Instructions", "A", "partial"),
    Criterion("3.3.3", "Error Suggestion", "AA", "manual"),
    Criterion("3.3.4", "Error Prevention (Legal, Financial, Data)", "AA", "manual"),
    Criterion("3.3.7", "Redundant Entry", "A", "manual", new_in_2_2=True),
    Criterion("3.3.8", "Accessible Authentication (Minimum)", "AA", "manual", new_in_2_2=True),
    Criterion("4.1.2", "Name, Role, Value", "A", "partial"),
    Criterion("4.1.3", "Status Messages", "AA", "partial"),
]

CRITERIA_BY_NUMBER: dict[str, Criterion] = {c.number: c for c in _CRITERIA}

# Criteria new in WCAG 2.2 that public sector bodies began being assessed against
# on 1 Oct 2024 — surfaced prominently because teams migrating from 2.1 miss them.
NEW_IN_2_2: list[str] = [c.number for c in _CRITERIA if c.new_in_2_2]


def criteria(level: str = "AA") -> list[Criterion]:
    """Return criteria up to and including the given level (AA includes A)."""
    level = level.upper()
    if level == "A":
        return [c for c in _CRITERIA if c.level == "A"]
    return list(_CRITERIA)  # AA (and AAA fallback) — we catalogue A + AA


def manual_criteria(level: str = "AA") -> list[Criterion]:
    """Criteria that cannot be fully automated and need human review."""
    return [c for c in criteria(level) if c.automation in ("manual", "partial")]


def understanding_url(number: str) -> str:
    c = CRITERIA_BY_NUMBER.get(number)
    return c.understanding_url if c else UNDERSTANDING_BASE
