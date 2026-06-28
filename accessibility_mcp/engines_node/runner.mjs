/**
 * Node engine runner for the Accessibility MCP server.
 *
 * Invoked by the Python `node_bridge` as:
 *     node runner.mjs <input-json-file>
 *
 * Input JSON: {
 *   engines: ["pa11y","lighthouse","ibm"],  // which Node engines to run
 *   url:     "https://...",                 // OR
 *   htmlFile:"/tmp/x.html",                 // a local file to audit (file://)
 *   steps:   [{action,selector,value,ms}],  // optional interactions before audit
 *   cookies: [{name,value,domain,path}],    // optional cookies (IBM/Playwright path)
 *   timeoutMs: 30000
 * }
 *
 * Output JSON (stdout): { engines: { <name>: {ok, ...}|{ok:false,error} } }
 *
 * Engines are heterogeneous by necessity:
 *   - pa11y    : uses its own Puppeteer browser (cannot share a Playwright page);
 *                audits by URL, replaying `steps` as pa11y actions.
 *   - lighthouse: own Chrome via chrome-launcher; audits by URL (no steps).
 *   - ibm      : driven through a Playwright page, so it sees the full interactive
 *                state (steps + cookies). Needs network egress to its rule archive.
 * All logging goes to stderr so stdout carries only the result JSON.
 */

import fs from "fs";
import { chromium } from "playwright-core";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const log = (...a) => process.stderr.write(a.join(" ") + "\n");

const CHROME =
  process.env.ACCESSIBILITY_MCP_CHROMIUM || process.env.CHROME || undefined;
const LAUNCH_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"];

function readInput() {
  const path = process.argv[2];
  if (!path) throw new Error("usage: node runner.mjs <input-json-file>");
  return JSON.parse(fs.readFileSync(path, "utf8"));
}

function targetUrl(input) {
  if (input.url) return input.url;
  if (input.htmlFile) return "file://" + input.htmlFile;
  return "about:blank";
}

// --- pa11y ---------------------------------------------------------------- //

function stepsToPa11yActions(steps = []) {
  const actions = [];
  for (const s of steps) {
    if (s.action === "click" && s.selector) {
      actions.push(`click element ${s.selector}`);
    } else if (s.action === "fill" && s.selector) {
      actions.push(`set field ${s.selector} to ${s.value ?? ""}`);
    } else if (s.action === "wait" && s.selector) {
      actions.push(`wait for element ${s.selector} to be visible`);
    }
  }
  return actions;
}

async function runPa11y(input) {
  const pa11y = require("pa11y");
  const res = await pa11y(targetUrl(input), {
    runners: ["htmlcs", "axe"],
    standard: "WCAG2AA",
    includeWarnings: true,
    timeout: input.timeoutMs ?? 30000,
    actions: stepsToPa11yActions(input.steps),
    chromeLaunchConfig: { executablePath: CHROME, args: LAUNCH_ARGS },
  });
  return {
    ok: true,
    issues: res.issues.map((i) => ({
      code: i.code,
      type: i.type, // error | warning | notice
      message: i.message,
      selector: i.selector,
      context: i.context,
      runner: i.runner,
    })),
  };
}

// --- lighthouse ----------------------------------------------------------- //

async function runLighthouse(input) {
  const chromeLauncher = await import("chrome-launcher");
  const lighthouse = (await import("lighthouse")).default;
  const chrome = await chromeLauncher.launch({
    chromePath: CHROME,
    chromeFlags: ["--headless", ...LAUNCH_ARGS],
  });
  try {
    const rr = await lighthouse(targetUrl(input), {
      onlyCategories: ["accessibility"],
      output: "json",
      port: chrome.port,
    });
    const lhr = rr.lhr;
    const audits = Object.values(lhr.audits)
      .filter((a) => a.score !== null && a.score < 1)
      .map((a) => ({
        id: a.id,
        title: a.title,
        description: a.description,
        score: a.score,
        items: (a.details && a.details.items
          ? a.details.items
          : []
        )
          .slice(0, 25)
          .map((it) => ({
            selector:
              (it.node && (it.node.selector || it.node.snippet)) || "",
            snippet: (it.node && it.node.snippet) || "",
          })),
      }));
    return {
      ok: true,
      score: lhr.categories.accessibility.score,
      audits,
    };
  } finally {
    await chrome.kill();
  }
}

// --- IBM Equal Access ----------------------------------------------------- //

async function applyPlaywrightSteps(page, steps = []) {
  for (const s of steps) {
    if (s.action === "click" && s.selector) await page.click(s.selector);
    else if (s.action === "fill" && s.selector)
      await page.fill(s.selector, s.value ?? "");
    else if (s.action === "wait" && s.selector)
      await page.waitForSelector(s.selector);
    else if (s.action === "wait" && s.ms) await page.waitForTimeout(s.ms);
    else if (s.action === "navigate" && s.value)
      await page.goto(s.value, { waitUntil: "load" });
  }
}

async function runIbm(input) {
  const aChecker = require("accessibility-checker");
  const browser = await chromium.launch({
    executablePath: CHROME,
    args: LAUNCH_ARGS,
  });
  try {
    const context = await browser.newContext();
    if (input.cookies && input.cookies.length) {
      await context.addCookies(input.cookies);
    }
    const page = await context.newPage();
    await page.goto(targetUrl(input), { waitUntil: "load" });
    await applyPlaywrightSteps(page, input.steps);
    const r = await aChecker.getCompliance(page, "accessibility-mcp-scan");
    const report = r.report || r;
    const results = (report.results || [])
      .filter((x) => x.value && (x.value[1] === "FAIL" || x.value[1] === "POTENTIAL"))
      .map((x) => ({
        ruleId: x.ruleId,
        message: x.message,
        level: x.value[1], // FAIL | POTENTIAL
        value: x.value, // [ "VIOLATION"|"RECOMMENDATION", "FAIL"|... ]
        path: x.path && x.path.dom,
        snippet: x.snippet,
        help: x.help || (x.messageArgs && x.messageArgs.help) || "",
      }));
    return {
      ok: true,
      counts: report.summary && report.summary.counts,
      results,
    };
  } finally {
    try {
      await aChecker.close();
    } catch (_) {}
    await browser.close();
  }
}

const RUNNERS = { pa11y: runPa11y, lighthouse: runLighthouse, ibm: runIbm };

async function main() {
  const input = readInput();
  const out = { engines: {} };
  for (const name of input.engines || []) {
    const fn = RUNNERS[name];
    if (!fn) {
      out.engines[name] = { ok: false, error: `unknown engine '${name}'` };
      continue;
    }
    try {
      out.engines[name] = await fn(input);
    } catch (e) {
      log(`[${name}] error:`, e && e.message);
      out.engines[name] = { ok: false, error: (e && e.message) || String(e) };
    }
  }
  process.stdout.write(JSON.stringify(out));
}

main().catch((e) => {
  process.stdout.write(JSON.stringify({ engines: {}, fatal: String(e && e.message || e) }));
  process.exit(1);
});
