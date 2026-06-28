# Accessibility MCP — WCAG 2.2 AA (GOV.UK standard)

A [Model Context Protocol](https://modelcontextprotocol.io) server that audits web
pages and sites for **WCAG 2.2 level AA** accessibility, aligned with the
[GOV.UK / GDS standard](https://www.gov.uk/guidance/accessibility-requirements-for-public-sector-websites-and-apps)
that UK public sector bodies are legally required to meet (since 1 October 2024).

It runs the industry-standard [axe-core](https://github.com/dequelabs/axe-core)
engine inside a real headless Chromium (via Playwright), layers **GOV.UK-specific
checks** and remediation guidance on top, and returns results as structured JSON,
a human-readable Markdown report, and a **GDS-style compliance summary**.

> **Honest by design.** Automated testing detects only ~30–40% of WCAG issues.
> Every report separates *automated failures*, *needs manual review*, and *passed*
> checks, and any unverified AA criterion keeps the status at "partially compliant".
> This tool is a starting point for, not a replacement for, a full manual audit.

## Tools

| Tool | Description |
| --- | --- |
| `audit_url` | Audit one live page (loads it in headless Chromium). |
| `audit_html` | Audit a raw HTML string / component snippet (no network fetch). |
| `audit_site` | Crawl a site (same origin) and audit each page; aggregated summary. |
| `list_wcag_rules` | Catalogue of WCAG 2.2 criteria checked, with automation coverage. |
| `generate_accessibility_statement` | Draft a GOV.UK-format accessibility statement from an audit. |

Each audit tool returns:
- `json` — structured, machine-readable results (violations, severity, WCAG
  criteria, affected selectors, remediation);
- `markdown_report` — a human-readable report grouped by severity;
- `gds_summary` — a GOV.UK-flavoured *compliant / partially compliant / not
  compliant* summary with reasons;
- `audit_id` — pass it to `generate_accessibility_statement` to reuse the result.

## What it checks

- **Full axe-core WCAG 2.2 rule set** (`wcag2a`, `wcag2aa`, `wcag21a`,
  `wcag21aa`, `wcag22aa`) — contrast, alt text, labels, names, landmarks, etc.
- **GOV.UK custom checks** — accessibility-statement link presence, "Skip to main
  content" skip link, a single `<main>` landmark, and GOV.UK Design System usage.
- **WCAG 2.2 awareness** — flags the criteria new in 2.2 (2.4.11, 2.5.7, 2.5.8,
  3.2.6, 3.3.7, 3.3.8) and marks non-automatable criteria as *needs manual review*
  rather than silently passing them.

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
# Chromium: this server reuses an existing Playwright Chromium if present
# (see configuration), otherwise install one:
playwright install chromium
```

axe-core is vendored in `accessibility_mcp/vendor/axe.min.js` — no CDN needed.

## Running

```bash
# Run directly over stdio:
accessibility-mcp
# or
python -m accessibility_mcp.server
```

### Register with an MCP client

Add to your client config (e.g. Claude Desktop `claude_desktop_config.json`, or
the example `mcp.json` in this repo):

```json
{
  "mcpServers": {
    "accessibility": {
      "command": "accessibility-mcp"
    }
  }
}
```

If you installed into a virtualenv, point `command` at that venv's executable, e.g.
`/path/to/.venv/bin/accessibility-mcp`.

## Configuration (environment variables)

| Variable | Default | Purpose |
| --- | --- | --- |
| `ACCESSIBILITY_MCP_CHROMIUM` | auto-detect | Explicit Chromium executable path. |
| `PLAYWRIGHT_BROWSERS_PATH` | (Playwright default) | Searched for an installed Chromium build. |
| `ACCESSIBILITY_MCP_PROXY` / `HTTPS_PROXY` | none | Outbound proxy for `audit_url` / `audit_site`. |
| `ACCESSIBILITY_MCP_PAGE_TIMEOUT_MS` | `30000` | Page load timeout. |
| `ACCESSIBILITY_MCP_MAX_PAGES` | `20` | Default crawl page limit. |
| `ACCESSIBILITY_MCP_MAX_DEPTH` | `2` | Default crawl depth limit. |

`audit_url` / `audit_site` need outbound network access to the target site. In
locked-down environments behind an egress policy, set `HTTPS_PROXY` (Chromium is
pointed at it automatically); `audit_html` needs no network.

## Development

```bash
pip install -e ".[dev]"
pytest                 # unit + browser-backed integration tests (local fixtures)
```

The integration tests drive a real headless Chromium against the HTML fixtures in
`tests/fixtures/`, so they require a working Chromium but no network access.

## Architecture

```
accessibility_mcp/
  server.py            FastMCP entry point — registers the 5 tools (stdio)
  audit.py             High-level orchestration (URL / HTML / site)
  config.py            WCAG tags, browser/proxy discovery, timeouts, limits
  engine/              browser.py, axe_runner.py, crawler.py
  rules/               wcag22.py (criteria catalogue), govuk_checks.py, remediation.py
  reporting/           models.py, builder.py, json/markdown/gds renderers
  vendor/axe.min.js    Pinned axe-core bundle
```

## Disclaimer

This server helps identify accessibility problems and draft an accessibility
statement. It does not, on its own, establish legal compliance. A full manual
audit (keyboard operation, screen-reader testing, focus order, captions, etc.) is
required to claim conformance with WCAG 2.2 AA.
