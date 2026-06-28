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
    assert {"list_engines", "list_wcag_rules", "list_axe_rules",
            "generate_accessibility_statement"} <= names
    # Per-rule tools (on by default)
    axe_tools = {n for n in names if n.startswith("axe_")}
    assert len(axe_tools) > 80
    assert "axe_color_contrast" in axe_tools


def test_list_engines_reports_axe_available():
    info = server.list_engines()
    assert info["engines"]["axe"]["available"] is True
    assert info["default_engines"] == config.DEFAULT_ENGINES


def test_list_axe_rules_wcag_filter():
    all_rules = server.list_axe_rules(wcag_only=False)
    wcag_rules = server.list_axe_rules(wcag_only=True)
    assert all_rules["total"] >= wcag_rules["total"] > 0
