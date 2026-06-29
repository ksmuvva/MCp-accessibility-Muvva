"""Integration tests for multi-engine auditing and interactive sessions.

These drive a real headless Chromium and the Node engine runner against a local
fixture server (no external network needed).
"""

from __future__ import annotations

import pytest

from accessibility_mcp import audit, config
from accessibility_mcp.engine import session as session_mod

node_required = pytest.mark.skipif(
    not (bool(config.NODE_EXECUTABLE) and config.NODE_RUNNER.exists() and (config.NODE_ENGINES_DIR / "node_modules").is_dir()),
    reason="Node engines not installed (run accessibility_mcp/engines_node/setup.sh)",
)


@pytest.mark.asyncio
async def test_axe_only_audit(fixture_server):
    result = await audit.audit_url(f"{fixture_server}/failing.html", engines=["axe"])
    assert result.ok
    assert result.engines_used == ["axe"]
    assert result.violation_count > 0
    assert all(f.source in ("axe-core", "govuk") for f in result.violations)


@node_required
@pytest.mark.asyncio
async def test_multi_engine_audit_collects_all_sources(fixture_server):
    result = await audit.audit_url(
        f"{fixture_server}/failing.html", engines=["axe", "pa11y", "lighthouse"]
    )
    assert result.ok
    # axe-core is driven directly and must always contribute on a broken page.
    sources = {f.source for f in result.violations}
    assert "axe-core" in sources
    # Aggregation works: findings span more than one engine source.
    assert len(sources) >= 2
    # Every requested Node engine must have *run*: it either contributed a finding
    # (violation or needs-review) or recorded a captured engine-error. This stays
    # robust across Chrome versions where a given engine may surface 0 issues,
    # without letting a silently-broken engine pass unnoticed.
    all_sources = {f.source for f in result.violations} | {f.source for f in result.needs_review}
    for engine in ("pa11y", "lighthouse"):
        assert engine in all_sources or engine in result.engine_errors, (
            f"{engine} neither produced findings nor recorded an engine error; "
            f"sources={all_sources}, engine_errors={result.engine_errors}"
        )


@node_required
@pytest.mark.asyncio
async def test_ibm_offline_is_engine_error_not_crash(fixture_server):
    # IBM needs egress to its rule archive; offline it must degrade gracefully.
    result = await audit.audit_url(f"{fixture_server}/failing.html", engines=["axe", "ibm"])
    assert result.ok  # the audit as a whole still succeeds
    # Either IBM produced findings (egress open) or recorded a clean engine error.
    assert "ibm" in result.engines_used
    if "ibm" in result.engine_errors:
        assert isinstance(result.engine_errors["ibm"], str)


@pytest.mark.asyncio
async def test_single_rule_audit(fixture_server):
    result = await audit.audit_rule("image-alt", url=f"{fixture_server}/failing.html")
    assert result.ok
    ids = {v.id for v in result.violations}
    assert ids == {"image-alt"} or "image-alt" in ids


@pytest.mark.asyncio
async def test_dedicated_axe_tool(fixture_server):
    from accessibility_mcp import server
    payload = await server.audit_axe(url=f"{fixture_server}/failing.html")
    assert payload["engines_used"] == ["axe"]
    assert payload["json"]["violations"]


@node_required
@pytest.mark.asyncio
async def test_dedicated_pa11y_tool(fixture_server):
    from accessibility_mcp import server
    payload = await server.audit_pa11y(url=f"{fixture_server}/failing.html")
    assert payload["engines_used"] == ["pa11y"]
    # axe-core must NOT have run; GOV.UK checks always run as a complementary layer.
    sources = {v["source"] for v in payload["json"]["violations"]}
    assert "axe-core" not in sources
    assert sources <= {"pa11y", "govuk"}


@pytest.mark.asyncio
async def test_automated_checks_suite(fixture_server):
    from accessibility_mcp.rules import automated_checks
    result = await audit.audit_rules(
        automated_checks.automated_rule_ids("AA"), url=f"{fixture_server}/failing.html"
    )
    assert result.ok
    ids = {v.id for v in result.violations}
    # The broken fixture should trip multiple automated checks.
    assert "image-alt" in ids


@pytest.mark.asyncio
async def test_grouped_audit_perceivable(fixture_server):
    # The perceivable group should catch image-alt / color-contrast on the fixture.
    from accessibility_mcp.rules import groups
    result = await audit.audit_rules(
        groups.principle_groups()["perceivable"], url=f"{fixture_server}/failing.html"
    )
    assert result.ok
    ids = {v.id for v in result.violations}
    assert "image-alt" in ids


@pytest.mark.asyncio
async def test_grouped_audit_color_category(fixture_server):
    from accessibility_mcp.rules import groups
    result = await audit.audit_rules(
        groups.category_groups()["color"], url=f"{fixture_server}/failing.html"
    )
    assert result.ok
    # Only colour rules run; every finding must be a colour rule.
    assert all(v.id in groups.category_groups()["color"] for v in result.violations)


@pytest.mark.asyncio
async def test_interactive_session_flow(fixture_server):
    manager = session_mod.SessionManager()
    session = await manager.open()
    try:
        await session.page.goto(f"{fixture_server}/failing.html", wait_until="load")
        result = await audit.audit_open_page(session.page, engines=["axe"])
        assert result.ok
        assert result.violation_count > 0
    finally:
        await manager.close(session.id)
    assert manager.count == 0
