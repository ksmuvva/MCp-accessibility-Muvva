"""Tests for MCP tool registration (bundled, navigation, per-rule, catalogue)."""

from __future__ import annotations

import pytest

from accessibility_mcp import config, server


@pytest.mark.asyncio
async def test_all_tool_categories_registered():
    tools = await server.mcp.list_tools()
    names = {t.name for t in tools}

    # Bundled audits
    assert {"audit_url", "audit_html", "audit_site"} <= names
    # Dedicated single-engine tools
    assert {"audit_axe", "audit_pa11y", "audit_lighthouse", "audit_ibm"} <= names
    # Navigation
    assert {
        "browser_open", "browser_navigate", "browser_click", "browser_fill",
        "browser_wait", "browser_snapshot", "audit_current_page", "browser_close",
    } <= names
    # Catalogue / reporting
    assert {"list_engines", "list_wcag_rules", "list_axe_rules", "list_groups",
            "generate_accessibility_statement"} <= names
    # Automated-check suite + catalogues. The per-criterion check_wcag_<n> tools
    # were consolidated into audit_automated_checks (see the 168->41 tool reduction).
    assert {"audit_automated_checks", "list_automated_checks", "list_manual_checks"} <= names
    # Per-rule auditing is one generic tool, not ~100 axe_<rule> tools.
    assert "axe_check_rule" in names
    # Grouped tools (on by default): WCAG principles + axe categories
    assert {"audit_perceivable", "audit_operable", "audit_understandable",
            "audit_robust"} <= names
    group_cats = {n for n in names if n.startswith("audit_group_")}
    assert len(group_cats) >= 5
    assert "audit_group_color" in group_cats


def test_list_groups_structure():
    info = server.list_groups()
    assert "audit_perceivable" in info["wcag_principle_groups"]
    assert info["wcag_principle_groups"]["audit_perceivable"]["rule_count"] > 0
    assert any("color" in k for k in info["axe_category_groups"])


def test_list_engines_reports_axe_available():
    info = server.list_engines()
    assert info["engines"]["axe"]["available"] is True
    assert info["default_engines"] == config.DEFAULT_ENGINES


def test_list_axe_rules_wcag_filter():
    all_rules = server.list_axe_rules(wcag_only=False)
    wcag_rules = server.list_axe_rules(wcag_only=True)
    assert all_rules["total"] >= wcag_rules["total"] > 0
