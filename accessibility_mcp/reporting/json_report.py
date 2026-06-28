"""Structured JSON serialisation of audit results.

Thin wrappers over pydantic ``model_dump`` so MCP tools can return machine-readable
results that agents can act on directly.
"""

from __future__ import annotations

from accessibility_mcp.reporting.models import PageAudit, SiteAudit


def page_to_dict(audit: PageAudit) -> dict:
    return audit.model_dump(mode="json")


def site_to_dict(audit: SiteAudit) -> dict:
    return audit.model_dump(mode="json")
