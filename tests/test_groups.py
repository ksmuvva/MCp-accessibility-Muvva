"""Unit tests for the rule grouping module."""

from __future__ import annotations

from accessibility_mcp.rules import groups


def test_principle_groups_cover_four_principles():
    pg = groups.principle_groups()
    assert {"perceivable", "operable", "understandable", "robust"} <= set(pg)
    # color-contrast is a Perceivable (1.4.3) rule.
    assert "color-contrast" in pg["perceivable"]


def test_category_groups_include_color_and_forms():
    cg = groups.category_groups()
    assert "color" in cg
    assert "color-contrast" in cg["color"]
    assert any("forms" in c for c in cg)


def test_category_tool_name():
    assert groups.category_tool_name("color") == "audit_group_color"
    assert groups.category_tool_name("text-alternatives") == "audit_group_text_alternatives"
