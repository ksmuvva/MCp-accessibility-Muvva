"""Unit tests for the automated-checks derivation and tools."""

from __future__ import annotations

from accessibility_mcp import server
from accessibility_mcp.rules import automated_checks


def test_automatable_criteria_include_contrast():
    auto = automated_checks.automatable_criteria("AA")
    assert "1.4.3" in auto
    assert "color-contrast" in auto["1.4.3"]


def test_automated_and_manual_are_disjoint_and_cover_catalogue():
    auto = set(automated_checks.automatable_criteria("AA"))
    manual = {c.number for c in automated_checks.manual_only_criteria("AA")}
    assert auto.isdisjoint(manual)
    # A criterion is either automatable or manual — never lost.
    from accessibility_mcp.rules import wcag22
    all_numbers = {c.number for c in wcag22.criteria("AA")}
    assert auto | manual == all_numbers


def test_manual_includes_non_automatable_2_2_criterion():
    manual = {c.number for c in automated_checks.manual_only_criteria("AA")}
    # 2.5.7 Dragging Movements has no axe rule — must be a manual check.
    assert "2.5.7" in manual


def test_criterion_tool_name():
    assert automated_checks.criterion_tool_name("1.4.3") == "check_wcag_1_4_3"


def test_automated_rule_ids_is_union():
    ids = set(automated_checks.automated_rule_ids("AA"))
    for rules in automated_checks.automatable_criteria("AA").values():
        assert set(rules) <= ids


def test_catalogue_tools():
    auto = server.list_automated_checks()
    manual = server.list_manual_checks()
    assert auto["total"] > 0
    assert manual["total"] > 0
    assert any(c["criterion"] == "1.4.3" for c in auto["checks"])
