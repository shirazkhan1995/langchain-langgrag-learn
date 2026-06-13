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

Run (in your own terminal — a real Chrome window opens and STAYS open):
    export OPENAI_API_KEY=sk-...
    python learn/08_playwright_mcp_agent.py
"""

import asyncio
import glob
import os

from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

SITE = "https://demo.playwright.dev/todomvc"


def find_chromium() -> str | None:
    """Find an already-installed Playwright Chromium so we don't depend on the MCP
    server downloading its own exact revision. On a fresh machine you'd run
    `npx playwright install chromium`, or pass `--browser chrome` if you have Chrome."""
    patterns = [
        os.path.expanduser(
            "~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/"
            "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        ),
        os.path.expanduser(
            "~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/Chromium.app/"
            "Contents/MacOS/Chromium"
        ),
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
    ]
    for pat in patterns:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


async def main() -> None:
    # 1) Point at the Playwright MCP server. `npx` launches it as a stdio subprocess.
    #    Headed by default so a window opens; add "--headless" for CI.
    #    --isolated: fresh in-memory profile, so repeated runs don't hit a
    #    "browser already in use" profile lock.
    args = ["@playwright/mcp@latest", "--isolated"]
    if chromium := find_chromium():
        args += ["--executable-path", chromium]
        print(f"[browser] using {chromium.split('/')[-1]}")

    client = MultiServerMCPClient(
        {"playwright": {"command": "npx", "args": args, "transport": "stdio"}}
    )

    # 2) Open ONE persistent session and keep it open for the whole run, so every
    #    tool call shares the SAME browser (stateful server — see the docstring).
    async with client.session("playwright") as session:
        tools = await load_mcp_tools(session)
        print(f"[mcp] Playwright MCP exposed {len(tools)} browser tools, e.g.:")
        for t in tools[:6]:
            print(f"      - {t.name}: {t.description.splitlines()[0][:64]}")

        # 3) Build a ReAct agent (lesson-6 loop, prebuilt) with those tools.
        #    gpt-4o-mini: cheaper + much higher tokens-per-minute than gpt-4o (big
        #    accessibility-tree snapshots resent each turn exhaust gpt-4o's 30k TPM).
        #    parallel_tool_calls=False: one browser can't take concurrent calls.
        system_prompt = (
            "You control a REAL web browser through the provided tools. "
            "Always: browser_navigate, then browser_snapshot to read the "
            "accessibility tree, then act (type/click) and snapshot to verify. "
            "Work in as few steps as possible. Never claim you can't access websites."
        )
        model = init_chat_model(
            "openai:gpt-4o-mini", temperature=0, max_retries=3
        ).bind_tools(tools, parallel_tool_calls=False)
        agent = create_react_agent(model, tools, prompt=system_prompt)

        # 4) A real, interactive test flow — the MODEL decides the steps.
        task = (
            f"Go to {SITE}. Add two todos: 'Write Playwright tests' and 'Ship "
            "feature'. Then tell me exactly how many items the footer says are left, "
            "and list the todo texts. Be concise."
        )
        print(f"\n[task] {task}\n")

        # recursion_limit caps the agent loop so a stuck run stops cleanly instead
        # of spinning (a max-iteration guard — the reliability point from §6.5).
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": task}]},
            config={"recursion_limit": 20},
        )

    # 5) Show the tool calls the model chose, then the final answer.
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


if __name__ == "__main__":
    asyncio.run(main())
