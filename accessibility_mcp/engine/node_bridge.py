"""Bridge to the Node engine runner (pa11y / Lighthouse / IBM Equal Access).

Spawns ``node runner.mjs <input.json>`` as a subprocess, passing the audit target
(URL or HTML file), optional interaction steps and cookies, and the engines to run.
Returns the parsed per-engine results. Designed to never raise for engine-level
problems: a missing Node install, a crashed runner, or a single engine failing all
surface as structured ``{ok: False, error: ...}`` entries so the rest of an audit
still succeeds.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path

from accessibility_mcp import config


def _engine_error(engines: list[str], message: str) -> dict:
    return {"engines": {e: {"ok": False, "error": message} for e in engines}}


async def run_node_engines(
    engines: list[str],
    *,
    url: str | None = None,
    html: str | None = None,
    steps: list[dict] | None = None,
    cookies: list[dict] | None = None,
    level: str = "AA",
    timeout_ms: int | None = None,
) -> dict:
    """Run the requested Node engines and return ``{"engines": {name: result}}``."""
    engines = [e for e in engines if e in config.NODE_ENGINES]
    if not engines:
        return {"engines": {}}

    if not (bool(config.NODE_EXECUTABLE) and config.NODE_RUNNER.exists() and (config.NODE_ENGINES_DIR / "node_modules").is_dir()):
        return _engine_error(
            engines,
            "Node engines are not installed. Run "
            "accessibility_mcp/engines_node/setup.sh (needs Node.js).",
        )

    timeout_ms = timeout_ms or config.PAGE_TIMEOUT_MS
    tmp_html: str | None = None
    input_payload: dict = {
        "engines": engines,
        "steps": steps or [],
        "cookies": cookies or [],
        "level": level,
        "timeoutMs": timeout_ms,
    }
    if url:
        input_payload["url"] = url
    elif html is not None:
        # Engines need a navigable target; write the HTML to a temp file (file://).
        fd, tmp_html = tempfile.mkstemp(suffix=".html", prefix="a11y-mcp-")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(html)
        input_payload["htmlFile"] = tmp_html
    else:
        return _engine_error(engines, "No url or html provided to Node engines.")

    fd, input_file = tempfile.mkstemp(suffix=".json", prefix="a11y-mcp-in-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(input_payload, fh)

    env = dict(os.environ)
    if config.CHROMIUM_EXECUTABLE:
        env["ACCESSIBILITY_MCP_CHROMIUM"] = config.CHROMIUM_EXECUTABLE

    try:
        proc = await asyncio.create_subprocess_exec(
            config.NODE_EXECUTABLE,
            str(config.NODE_RUNNER),
            input_file,
            cwd=str(config.NODE_ENGINES_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        # Generous wall-clock budget: several engines may each load a page.
        budget = (timeout_ms / 1000) * len(engines) + 60
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=budget)
        except asyncio.TimeoutError:
            proc.kill()
            return _engine_error(engines, f"Node engines timed out after {budget:.0f}s.")

        if not stdout.strip():
            tail = stderr.decode("utf-8", "replace")[-300:]
            return _engine_error(engines, f"Node runner produced no output. {tail}")

        try:
            return json.loads(stdout.decode("utf-8"))
        except json.JSONDecodeError as exc:
            return _engine_error(engines, f"Could not parse Node runner output: {exc}")
    except FileNotFoundError:
        return _engine_error(engines, "Node executable not found.")
    finally:
        Path(input_file).unlink(missing_ok=True)
        if tmp_html:
            Path(tmp_html).unlink(missing_ok=True)
