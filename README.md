# Accessibility MCP — WCAG 2.2 AA (GOV.UK standard)

A [Model Context Protocol](https://modelcontextprotocol.io) server that audits web
pages and sites for **WCAG 2.2 level AA** accessibility, aligned with the
[GOV.UK / GDS standard](https://www.gov.uk/guidance/accessibility-requirements-for-public-sector-websites-and-apps)
that UK public sector bodies are legally required to meet (since 1 October 2024).

It drives a real headless Chromium (via Playwright) and runs up to **four
independent accessibility engines** — [axe-core](https://github.com/dequelabs/axe-core),
[pa11y](https://github.com/pa11y/pa11y) (HTML_CodeSniffer + axe),
[Lighthouse](https://github.com/GoogleChrome/lighthouse) and
[IBM Equal Access](https://github.com/IBMa/equal-access) — layers **GOV.UK-specific
checks** and remediation guidance on top, and returns results as structured JSON,
a human-readable Markdown report, and a **GDS-style compliance summary**.

It can drive **interactive journeys** (navigate, click, fill, log in) and audit the
resulting state, and it exposes **one tool per axe-core rule** (~100) for
fine-grained checks.

> **Honest by design.** Automated testing detects only ~30–40% of WCAG issues.
> Every report separates *automated failures*, *needs manual review*, and *passed*
> checks, and any unverified AA criterion keeps the status at "partially compliant".
> This tool is a starting point for, not a replacement for, a full manual audit.

## Tools

**Bundled audits (multi-engine):**

| Tool | Description |
| --- | --- |
| `audit_url` | Audit one live page; supports `engines` and interaction `steps`. |
| `audit_html` | Audit a raw HTML string / component snippet (no network fetch). |
| `audit_site` | Crawl a site (same origin) and audit each page; aggregated summary. |

**Dedicated single-engine audits** (take `url`, `html` or `session_id`):

| Tool | Description |
| --- | --- |
| `audit_axe` | axe-core only (plus GOV.UK checks). |
| `audit_pa11y` | pa11y only (HTML_CodeSniffer + axe runners). |
| `audit_lighthouse` | Lighthouse accessibility only. |
| `audit_ibm` | IBM Equal Access only. |

**Interactive navigation (stateful browser session):**

| Tool | Description |
| --- | --- |
| `browser_open` | Open a session; returns a `session_id`. |
| `browser_navigate` / `browser_click` / `browser_fill` / `browser_wait` | Drive the page. |
| `browser_snapshot` | Current url, title and visible text. |
| `audit_current_page` | Audit the current post-interaction state. |
| `browser_close` | Close the session. |

**Per-axe-rule tools (~100, on by default):** one tool per axe rule, e.g.
`axe_color_contrast`, `axe_image_alt`, `axe_label`. Each takes `url`, `html` or
`session_id`. Disable with `ACCESSIBILITY_MCP_PER_RULE_TOOLS=0`.

**Catalogue / reporting:**

| Tool | Description |
| --- | --- |
| `list_engines` | Available engines and whether the Node runner is installed. |
| `list_wcag_rules` | WCAG 2.2 criteria checked, with automation coverage. |
| `list_axe_rules` | All axe rules (each also exposed as its own tool). |
| `generate_accessibility_statement` | Draft a GOV.UK-format statement from an audit. |

Each audit tool returns:
- `json` — structured, machine-readable results (violations, severity, WCAG
  criteria, affected selectors, remediation);
- `markdown_report` — a human-readable report grouped by severity;
- `gds_summary` — a GOV.UK-flavoured *compliant / partially compliant / not
  compliant* summary with reasons;
- `audit_id` — pass it to `generate_accessibility_statement` to reuse the result.

## Engines

Choose engines per call via `engines=["axe","pa11y","lighthouse","ibm"]` (default
`["axe"]`). Findings from every engine are normalised to a common shape with WCAG
criteria and labelled by `source`, so you can cross-check results.

| Engine | Language | Notes |
| --- | --- | --- |
| `axe` | Python (in-process) | Deque axe-core, explicit WCAG 2.2 tags. Always available. |
| `pa11y` | Node | HTML_CodeSniffer + axe runners. Replays `steps` as pa11y actions. |
| `lighthouse` | Node | Google Lighthouse accessibility category. Audits by URL. |
| `ibm` | Node | IBM Equal Access. **Needs network egress to its rule archive** (`cdn.jsdelivr.net`); in locked-down networks it returns a structured engine-error instead of crashing the run. |

axe runs in-process; the other three run in a Node subprocess
(`accessibility_mcp/engines_node/`). If the Node runner is not installed, those
engines report a clear "not installed" error and axe still works.

## What it checks

- **Full axe-core WCAG 2.2 rule set** (`wcag2a`, `wcag2aa`, `wcag21a`,
  `wcag21aa`, `wcag22aa`) — contrast, alt text, labels, names, landmarks, etc.
- **pa11y / Lighthouse / IBM** — independent rulesets for cross-checking.
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

# Optional — pa11y, Lighthouse and IBM engines (needs Node.js):
bash accessibility_mcp/engines_node/setup.sh
```

axe-core is vendored in `accessibility_mcp/vendor/axe.min.js` — no CDN needed. The
per-rule tool catalogue (`vendor/axe-rules.json`) is generated by
`python scripts/generate_axe_rules.py` (only needed when updating axe-core).

The Node engines reuse the same Chromium as axe (no extra browser download). Only
`axe` is required; the others are optional and degrade gracefully if absent.

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
| `ACCESSIBILITY_MCP_PER_RULE_TOOLS` | `1` | Register ~100 per-axe-rule tools. Set `0` to disable. |
| `ACCESSIBILITY_MCP_NODE` | auto-detect | Path to the Node.js executable for the engine runner. |

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
  server.py            FastMCP entry point — bundled + nav + ~100 per-rule tools
  audit.py             Orchestration (URL / HTML / site / single rule / open page)
  config.py            WCAG tags, engines, browser/proxy/node discovery, limits
  engine/              browser.py, axe_runner.py, crawler.py, node_bridge.py, session.py
  engines_node/        Node runner for pa11y / Lighthouse / IBM (runner.mjs, setup.sh)
  rules/               wcag22.py, govuk_checks.py, remediation.py, normalize.py, axe_rules.py
  reporting/           models.py, builder.py, json/markdown/gds renderers
  vendor/              axe.min.js, axe-rules.json (per-rule catalogue)
scripts/generate_axe_rules.py   Regenerate vendor/axe-rules.json from axe-core
```

## Disclaimer

This server helps identify accessibility problems and draft an accessibility
statement. It does not, on its own, establish legal compliance. A full manual
audit (keyboard operation, screen-reader testing, focus order, captions, etc.) is
required to claim conformance with WCAG 2.2 AA.
