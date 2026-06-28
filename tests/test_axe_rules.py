"""Unit tests for the axe rule catalogue + per-rule tool naming."""

from __future__ import annotations

from accessibility_mcp.rules import axe_rules


def test_catalogue_loads():
    rules = axe_rules.all_rules()
    assert len(rules) > 80  # axe 4.x ships ~100 rules
    assert axe_rules.axe_version().startswith("4.")


def test_tool_name_sanitisation():
    rule = axe_rules.get_rule("color-contrast")
    assert rule is not None
    assert rule.tool_name == "axe_color_contrast"


def test_wcag_rules_subset():
    all_rules = axe_rules.all_rules()
    wcag = axe_rules.wcag_rules()
    assert 0 < len(wcag) <= len(all_rules)
    assert all(r.is_wcag for r in wcag)


def test_color_contrast_maps_to_criterion():
    rule = axe_rules.get_rule("color-contrast")
    assert "1.4.3" in rule.wcag_criteria
