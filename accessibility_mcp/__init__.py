"""Accessibility MCP — WCAG 2.2 AA auditing aligned with the GOV.UK / GDS standard.

Exposes accessibility-audit tools over the Model Context Protocol. Audits run the
industry-standard axe-core engine inside a real headless Chromium (via Playwright),
layer GOV.UK-specific checks and remediation guidance on top, and report results as
structured JSON, a human-readable Markdown report, and a GDS-style compliance summary.
"""

__version__ = "0.1.0"
