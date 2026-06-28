"""Automated-check definitions: the WCAG criteria a machine can actually test.

An "automated check" here is a WCAG 2.2 success criterion for which axe-core has
one or more rules — i.e. something we can verify automatically with reasonable
confidence. Criteria with no axe coverage are "manual checks" that require a human.

This module derives both sets from the axe catalogue + the WCAG 2.2 catalogue, and
powers the automated-check tools (a per-criterion tool each, a combined suite, and
the automated/manual split catalogues).
"""

from __future__ import annotations

from accessibility_mcp.rules import axe_rules, wcag22


def _sort_key(number: str) -> list[int]:
    return [int(part) for part in number.split(".")]


def automatable_criteria(level: str = "AA") -> dict[str, list[str]]:
    """Map WCAG criterion number -> axe rule ids that automate (part of) it.

    Only includes criteria present in the WCAG 2.2 catalogue up to ``level`` that
    have at least one axe rule mapped to them.
    """
    catalogue = {c.number for c in wcag22.criteria(level)}
    mapping: dict[str, set[str]] = {}
    for rule in axe_rules.all_rules():
        for crit in rule.wcag_criteria:
            if crit in catalogue:
                mapping.setdefault(crit, set()).add(rule.rule_id)
    return {
        number: sorted(mapping[number])
        for number in sorted(mapping, key=_sort_key)
    }


def automated_rule_ids(level: str = "AA") -> list[str]:
    """Every axe rule id that maps to a WCAG criterion at/below ``level``."""
    ids: set[str] = set()
    for rules in automatable_criteria(level).values():
        ids.update(rules)
    return sorted(ids)


def manual_only_criteria(level: str = "AA") -> list[wcag22.Criterion]:
    """WCAG criteria with no axe coverage — these require manual assessment."""
    automatable = set(automatable_criteria(level))
    return [c for c in wcag22.criteria(level) if c.number not in automatable]


def criterion_tool_name(number: str) -> str:
    """MCP tool name for a per-criterion automated check, e.g. '1.4.3' -> 'check_wcag_1_4_3'."""
    return "check_wcag_" + number.replace(".", "_")
