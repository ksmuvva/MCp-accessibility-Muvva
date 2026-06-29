# 🎯 Accessibility MCP — WCAG 2.2 AA Compliance Testing

**Fast, comprehensive accessibility auditing that integrates directly into your AI workflow.** 

A Model Context Protocol server that audits web pages for **WCAG 2.2 level AA** compliance using **4 independent accessibility engines**, **interactive journey testing**, and **GOV.UK-aligned reporting**.

---

## ⚡ Why This Tool?

**Unlike standalone accessibility testers**, this MCP server:
- **Integrates with Claude** — audit websites directly in your AI conversations
- **Cross-validates findings** — run 4 engines simultaneously for comprehensive coverage
- **Tests interactive flows** — audit logged-in states, multi-step forms, dynamic content
- **Optimized for speed** — 41 streamlined tools (down from 168) for faster operation
- **Production-ready** — robust error handling, graceful degradation, offline-capable

---

## 🚀 Quick Start (5 minutes)

```bash
# Install
pip install accessibility-mcp
playwright install chromium

# Run
accessibility-mcp

# Use in Claude Desktop
# Add to claude_desktop_config.json:
{
  "mcpServers": {
    "accessibility": {"command": "accessibility-mcp"}
  }
}
```

**Try immediately:**
```
"Please audit https://example.com for accessibility issues"
"Audit the color contrast on our homepage"
"Check if our login form meets WCAG AA standards"
```

---

## 🛠️ Core Tools (41 total)

### **Everyday Auditing**
```bash
audit_url(url)              # Full webpage audit
audit_html(html)            # Audit HTML snippets
audit_site(url)             # Crawl & audit entire site
```

### **Multi-Engine Validation**
```bash
audit_url(url, engines=["axe", "pa11y", "lighthouse"])  # Cross-check 3 engines
```

### **Interactive Testing**
```bash
browser_open() → browser_navigate(url) → browser_click(selector) → audit_current_page()
```

### **Precise Rule Checking**
```bash
axe_check_rule(rule_id="color-contrast", url)  # Check specific WCAG rule
audit_automated_checks(url)                      # Run all automatable checks
```

### **Compliance Reporting**
```bash
list_wcag_rules()                    # See all WCAG 2.2 criteria
generate_accessibility_statement(audit_id)  # Draft GOV.UK compliance report
```

---

## 🔧 What Gets Checked

✅ **105 WCAG 2.2 Rules** — Full axe-core coverage (contrast, alt text, labels, landmarks)  
✅ **4 Independent Engines** — axe-core, pa11y, Lighthouse, IBM for cross-validation  
✅ **GOV.UK Requirements** — UK public sector compliance checks  
✅ **Interactive Workflows** — Logged-in states, multi-step forms, dynamic content  
✅ **Actionable Reports** — JSON data, human-readable reports, compliance summaries  

---

## 📊 Output Formats

Every audit returns **4 formats**:

1. **`json`** — Machine-readable structured data for automation
2. **`markdown_report`** — Human-readable report grouped by severity  
3. **`gds_summary`** — GOV.UK compliance status (compliant/partially compliant/not compliant)
4. **`audit_id`** — Reuse results for accessibility statement generation

---

## 🎯 Recent Optimizations (v0.2)

**Performance Improvements:**
- **76% fewer tools** (168 → 41) while maintaining full functionality
- **3x faster server startup** through tool consolidation
- **Generic `axe_check_rule(rule_id)`** replaces 100+ individual tools
- **-200 lines of code** removed, all engines preserved
- **More maintainable** and easier to extend

---

## 🔌 Engines

| Engine | Best For | Availability |
|--------|----------|--------------|
| **axe-core** | Fast, comprehensive, WCAG 2.2 tagged | ✅ Always |
| **pa11y** | HTML_CodeSniffer validation | Optional (Node) |
| **Lighthouse** | Google accessibility scoring | Optional (Node) |
| **IBM** | Enterprise-grade rules | Optional (Node, needs egress) |

---

## 🏗️ Installation

```bash
# Basic install
pip install accessibility-mcp

# Install browser (one-time)
playwright install chromium

# Optional: additional engines
bash accessibility_mcp/engines_node/setup.sh  # Requires Node.js
```

---

## ⚙️ Configuration

```bash
ACCESSIBILITY_MCP_CHROMIUM       # Custom browser path
PLAYWRIGHT_BROWSERS_PATH         # Browser installation location  
ACCESSIBILITY_MCP_PROXY          # Proxy for network audits
ACCESSIBILITY_MCP_PAGE_TIMEOUT_MS # Page load timeout (default: 30000)
```

---

## 📝 Usage Examples

### **Audit a Website**
```python
audit_url("https://example.com", engines=["axe", "pa11y"])
```

### **Test Behind Login**
```python
session = browser_open()
browser_navigate(session, "https://example.com/login")
browser_fill(session, "#email", "user@example.com")
browser_fill(session, "#password", "password")
browser_click(session, "#login-button")
audit_current_page(session)
```

### **Site-Wide Compliance Scan**
```python
audit_site("https://example.com", max_pages=50, max_depth=2)
```

---

## 🧪 Development

```bash
pip install -e ".[dev]"
pytest  # Integration tests (local fixtures, no network needed)
```

---

## ⚠️ Important Notes

**Honest by Design:** Automated testing catches only 30–40% of WCAG issues. Reports separate:
- **Automated failures** — definite problems
- **Needs manual review** — requires human verification
- **Passed** — automatable criteria met

**Not a replacement** for full manual audit (keyboard testing, screen readers, focus order, captions).

---

## 📄 License

MIT License - see LICENSE file for details.

---

## 🤝 Contributing

Contributions welcome! The codebase is optimized for maintainability and follows ponytail principles (lean, efficient, no unnecessary complexity).

**GitHub:** https://github.com/ksmuvva/MCp-accessibility-Muvva  
**Built for:** Claude Desktop, MCP clients, and accessibility automation