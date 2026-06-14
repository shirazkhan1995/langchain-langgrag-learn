"""
LESSON 8 — Playwright MCP + a LangGraph agent (AI-augmented test automation).

THE SYNTHESIS of everything: agent loop (lesson 6) + tools-via-MCP + Playwright.

What's happening, in one breath:
  - Microsoft ships an official MCP server, `@playwright/mcp`, that exposes BROWSER
    automation as MCP tools (navigate, click, type, snapshot...).
  - It drives the browser via the ACCESSIBILITY TREE, not screenshots — so it's
    fast, deterministic, and token-cheap (no vision model needed).
  - `langchain-mcp-adapters` connects to that MCP server and turns its tools into
    LangChain tools, which we hand to a LangGraph ReAct agent.
  - Result: an LLM agent that DRIVES A REAL BROWSER from natural language.

STATEFUL vs STATELESS MCP (the key subtlety, and a great interview point):
  Playwright MCP is STATEFUL — the open browser/page IS shared state. If each tool
  call opened its own session (what client.get_tools() does), navigate would open a
  browser, then snapshot would open a DIFFERENT blank browser — state lost, and the
  agent loops forever opening/closing browsers. So we hold ONE persistent session
  open for the whole run via `client.session(...)` + `load_mcp_tools(session)`.

Target site: https://demo.playwright.dev/todomvc — Playwright's OWN demo TodoMVC app.

────────────────────────────────────────────────────────────────────────────────
Setup (once per machine — installs the matching Chromium, cross-platform):
    npx playwright install chromium

Run (HEADLESS by default — reliable on local, Wayland, containers, and CI alike):
    export OPENAI_API_KEY=sk-...
    python learn/08_playwright_mcp_agent.py

  There's no window to watch; you inspect what the agent did via the artifacts it
  writes to learn/_artifacts/ — a final-page.png screenshot plus per-step .yml
  snapshots. That's exactly how you observe a headless CI run.

  Want to watch live? HEADED=1 opens a real window where the desktop supports it
  (headed-over-MCP can be flaky on Linux/Wayland — see want_headless):
      HEADED=1 python learn/08_playwright_mcp_agent.py

  Env knobs: HEADED / HEADLESS, PWMCP_MODEL, PWMCP_SITE, PWMCP_OUTPUT_DIR,
  PLAYWRIGHT_CHROMIUM_PATH (force a specific browser binary).
"""

import asyncio
import glob
import json
import os
import tempfile

from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

# ── Config ──────────────────────────────────────────────────────────────────────
# Everything tunable lives here and is env-driven, so the SAME file runs unchanged on
# macOS, Linux, and CI. (Reading env up top — not scattered through the code — is the
# production habit: one place to see what the run depends on.)
SITE = os.getenv("PWMCP_SITE", "https://demo.playwright.dev/todomvc")
MODEL = os.getenv("PWMCP_MODEL", "openai:gpt-4o-mini")
# Where Playwright MCP writes artifacts (screenshot, per-step snapshots, console logs).
# Anchored to THIS file's dir so it's predictable no matter which directory you run from.
ARTIFACTS = os.getenv("PWMCP_OUTPUT_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "_artifacts"
)
SYSTEM_PROMPT = (
    "You control a REAL web browser through the provided tools. "
    "Always: browser_navigate, then browser_snapshot to read the accessibility tree, "
    "then act (type/click) and snapshot to verify. "
    "Work in as few steps as possible. Never claim you can't access websites."
)


# ── Environment & launch helpers ─────────────────────────────────────────────────
def want_headless() -> bool:
    """Decide headless vs headed. HEADLESS by default — it runs the SAME task reliably
    everywhere (local, Wayland, containers, CI) and is what production e2e actually uses.
    Opt into a visible window with HEADED=1 (or HEADLESS=0).

    Why headless is the default, not headed: a headed window needs a working display,
    AND when driven through @playwright/mcp over stdio, headed launches proved flaky on
    Linux/Wayland (the browser opens then closes: "Target page, context or browser has
    been closed"). Headless avoids the window system entirely. To *see* what the agent
    did, open the screenshot under learn/_artifacts/ — same as observing a CI run."""
    override = os.getenv("HEADLESS")
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes", "on"}
    if os.getenv("HEADED", "").strip().lower() in {"1", "true", "yes", "on"}:
        return False  # explicit opt-in to a visible window
    return True


def write_mcp_config(headless: bool) -> str:
    """Write a Playwright-MCP config that sets headless EXPLICITLY; return its path.

    Why this exists (the real bug behind "the browser never spun up"): despite the CLI
    help saying "headed by default", @playwright/mcp launches *headless* when driven
    over the stdio transport (which is how langchain-mcp-adapters connects). The task
    still completes — it just runs off-screen, so no window appears. There's no `--headed`
    flag (only `--headless` to force it off), so the deterministic, supported lever is a
    config file with browser.launchOptions.headless. Setting it explicitly both ways
    means we never rely on the server's ambiguous default."""
    cfg = {"browser": {"launchOptions": {"headless": headless}}}
    path = os.path.join(tempfile.gettempdir(), "pwmcp-config.json")
    with open(path, "w") as f:
        json.dump(cfg, f)
    return path


def find_chromium() -> str | None:
    """Best-effort path to an already-installed Playwright Chromium, so we can pin the
    MCP server to it instead of depending on it fetching its own exact revision. On a
    fresh machine the canonical bootstrap is `npx playwright install chromium`; if that
    has run, the MCP server finds its managed browser on its own and this can return
    None harmlessly.

    Cross-platform: Playwright caches browsers under a per-OS root, and the binary's
    name + subdirectory differ by platform AND have changed across versions
    (chrome-linux vs chrome-linux64, chrome-mac vs chrome-mac-arm64). Rather than
    hardcode every layout, recurse each cache root and match the known executable
    names. `chromium-*` (not `chromium_headless_shell-*`) keeps us on the full build."""
    explicit = os.getenv("PLAYWRIGHT_CHROMIUM_PATH")
    if explicit and os.path.exists(explicit):
        return explicit
    cache_roots = [
        os.path.expanduser("~/.cache/ms-playwright"),  # Linux
        os.path.expanduser("~/Library/Caches/ms-playwright"),  # macOS
        os.path.expanduser("~/AppData/Local/ms-playwright"),  # Windows
    ]
    # Most specific name first; macOS ships the "for Testing" build, Linux a bare chrome.
    binary_names = ["Google Chrome for Testing", "Chromium", "chrome.exe", "chrome"]
    for root in cache_roots:
        for name in binary_names:
            hits = sorted(
                glob.glob(os.path.join(root, "chromium-*", "**", name), recursive=True)
            )
            if hits:
                return hits[-1]  # highest revision (sorted by chromium-<rev>)
    return None


def build_server_args(headless: bool) -> list[str]:
    """Assemble the `npx @playwright/mcp` command-line — every launch decision in one
    place: explicit headless via --config, an isolated in-memory profile (so repeated
    runs don't hit a "browser already in use" lock), an artifact output dir, and a pin
    to a locally-installed Chromium when we find one. Prints what it chose so the wiring
    is visible to a learner."""
    args = [
        "@playwright/mcp@latest",
        "--isolated",
        "--config", write_mcp_config(headless),
        "--output-dir", ARTIFACTS,
    ]
    print(
        "[browser] headless (no window; CI-safe)"
        if headless
        else "[browser] headed — a real browser window will open"
    )
    if chromium := find_chromium():
        args += ["--executable-path", chromium]
        print(f"[browser] pinned to {os.path.basename(chromium)}")
    else:
        print(
            "[browser] no local Chromium found — MCP will use its managed browser; "
            "if launch fails, run: npx playwright install chromium"
        )
    return args


# ── Agent, observability, reporting ──────────────────────────────────────────────
def build_agent(tools):
    """A ReAct agent (the lesson-6 loop, prebuilt) wired to the MCP browser tools.
    - gpt-4o-mini: cheaper + much higher tokens-per-minute than gpt-4o (the big
      accessibility-tree snapshots resent each turn exhaust gpt-4o's 30k TPM fast).
    - parallel_tool_calls=False: one browser can't take concurrent tool calls."""
    model = init_chat_model(MODEL, temperature=0, max_retries=3).bind_tools(
        tools, parallel_tool_calls=False
    )
    return create_react_agent(model, tools, prompt=SYSTEM_PROMPT)


async def capture_screenshot(tools) -> None:
    """Save a screenshot of the final page — this is how you SEE a headless run, and the
    same artifact you'd upload from CI. Best-effort: a screenshot must never fail the run.
    MUST be called while the MCP session is still open (the browser closes on exit)."""
    shot = next((t for t in tools if t.name == "browser_take_screenshot"), None)
    if shot is None:
        return
    # Absolute path: the tool treats a bare filename as relative to the MCP server's
    # cwd, NOT --output-dir, so we pin the destination explicitly.
    shot_path = os.path.join(ARTIFACTS, "final-page.png")
    try:
        os.makedirs(ARTIFACTS, exist_ok=True)
        await shot.ainvoke({"filename": shot_path, "type": "png", "fullPage": True})
        print(f"\n[artifact] saved {shot_path} — open it to SEE the final page")
    except Exception as e:  # noqa: BLE001 — screenshot is non-essential
        print(f"\n[artifact] screenshot skipped ({type(e).__name__}: {e})")


def print_report(result) -> None:
    """Show the trajectory (the tool calls the MODEL chose) and the final answer."""
    print("=== agent trajectory (tool calls the MODEL chose) ===")
    for m in result["messages"]:
        for call in getattr(m, "tool_calls", None) or []:
            print(f"   -> {call['name']}({call['args']})")
        if m.__class__.__name__ == "ToolMessage":
            print(f"      <- {str(m.content).replace(chr(10), ' ')[:110]}")
    print("\n=== FINAL ANSWER ===")
    print(result["messages"][-1].content)
    print(
        "\nNote: an LLM agent just performed a real test flow on a real app via "
        "Playwright MCP — agent (lesson 6) + tools-over-MCP = AI-augmented testing."
    )


# ── Orchestration ────────────────────────────────────────────────────────────────
async def main() -> None:
    # 1) Configure the Playwright MCP server (launched by npx as a stdio subprocess).
    client = MultiServerMCPClient(
        {
            "playwright": {
                "command": "npx",
                "args": build_server_args(want_headless()),
                "transport": "stdio",
            }
        }
    )

    # 2) Hold ONE persistent session for the whole run — Playwright MCP is STATEFUL, so
    #    every tool call must share the SAME browser (see the module docstring).
    async with client.session("playwright") as session:
        tools = await load_mcp_tools(session)
        print(f"[mcp] Playwright MCP exposed {len(tools)} browser tools, e.g.:")
        for t in tools[:6]:
            print(f"      - {t.name}: {t.description.splitlines()[0][:64]}")

        # 3) Build the ReAct agent over those tools.
        agent = build_agent(tools)

        # 4) Run a real, interactive test flow — the MODEL sequences the steps itself.
        task = (
            f"Go to {SITE}. Add two todos: 'Write Playwright tests' and 'Ship "
            "feature'. Then tell me exactly how many items the footer says are left, "
            "and list the todo texts. Be concise."
        )
        print(f"\n[task] {task}\n")
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": task}]},
            # recursion_limit caps the agent loop so a stuck run stops cleanly instead
            # of spinning — a max-iteration guard (the reliability point from §6.5).
            config={"recursion_limit": 20},
        )

        # 5) Capture the screenshot WHILE the session is still open.
        await capture_screenshot(tools)

    # 6) Report the trajectory and the final answer (browser already closed — fine).
    print_report(result)


if __name__ == "__main__":
    asyncio.run(main())
