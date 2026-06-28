"""Logical groupings of axe-core rules for the grouped MCP tools.

Two grouping schemes, both derived from the axe rule catalogue so they stay in
sync with the vendored axe-core:

  * **WCAG principle** — Perceivable / Operable / Understandable / Robust, by the
    first digit of each rule's WCAG success criteria.
  * **axe category** — axe's own ``cat.*`` tags (colour, forms, keyboard, aria,
    tables, language, structure, etc.).

Each group resolves to a list of axe rule ids that the grouped tools run together.
"""

from __future__ import annotations

from accessibility_mcp.rules import axe_rules

# WCAG principle number -> human name.
PRINCIPLES: dict[str, str] = {
    "1": "perceivable",
    "2": "operable",
    "3": "understandable",
    "4": "robust",
}


def principle_groups() -> dict[str, list[str]]:
    """Map principle name -> axe rule ids whose WCAG criteria fall under it."""
    groups: dict[str, list[str]] = {name: [] for name in PRINCIPLES.values()}
    for rule in axe_rules.all_rules():
        principles_hit = {c.split(".")[0] for c in rule.wcag_criteria}
        for digit in principles_hit:
            name = PRINCIPLES.get(digit)
            if name:
                groups[name].append(rule.rule_id)
    return {name: ids for name, ids in groups.items() if ids}


def category_groups() -> dict[str, list[str]]:
    """Map axe category (the ``cat.*`` tag, prefix stripped) -> axe rule ids."""
    groups: dict[str, list[str]] = {}
    for rule in axe_rules.all_rules():
        for tag in rule.tags:
            if tag.startswith("cat."):
                category = tag[len("cat.") :]
                groups.setdefault(category, []).append(rule.rule_id)
    return groups


def category_tool_name(category: str) -> str:
    """MCP tool name for an axe category group, e.g. 'color' -> 'audit_group_color'."""
    safe = category.replace("-", "_").replace(".", "_")
    return f"audit_group_{safe}"
