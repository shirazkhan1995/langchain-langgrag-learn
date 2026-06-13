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
  - Result: an LLM agent that DRIVES A REAL BROWSER from natural language. That is
    "AI-augmented testing" — the agent can explore an app, author, or self-heal tests.

Target site: https://demo.playwright.dev/todomvc — Playwright's OWN demo TodoMVC app
(a real interactive web app, perfect for showing an agent perform a real test flow).

Mental model (ties to lesson 6 + the MCP talk-track):
    LLM (brain)        -> gpt-4o
    Orchestration loop -> create_react_agent (the agent<->tools loop)
    Tools              -> NOT hand-written @tool this time; pulled from an MCP SERVER
    The MCP server     -> @playwright/mcp, a separate process speaking the protocol

Run (in your own terminal — a real Chrome window opens and you watch it work):
    export OPENAI_API_KEY=sk-...
    python learn/08_playwright_mcp_agent.py

First run downloads @playwright/mcp via npx (needs internet).
"""

import asyncio
import glob
import os

from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
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
    #    The N+M win: we wrote zero browser tools — we connect to a standard server.
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

    # 2) Load the MCP server's tools as LangChain tools.
    tools = await client.get_tools()
    print(f"[mcp] Playwright MCP exposed {len(tools)} browser tools, e.g.:")
    for t in tools[:6]:
        print(f"      - {t.name}: {t.description.splitlines()[0][:64]}")

    # 3) Build a ReAct agent (lesson-6 loop, prebuilt) with those tools.
    system_prompt = (
        "You control a REAL web browser through the provided tools. "
        "Always: browser_navigate, then browser_snapshot to read the accessibility "
        "tree, then act (type/click) and snapshot again to verify. "
        "Never claim you cannot access websites — you can, via the tools."
    )
    # parallel_tool_calls=False: the browser is ONE session — force the agent to
    # call tools one at a time, or concurrent calls collide ("browser already in use").
    model = init_chat_model("openai:gpt-4o", temperature=0).bind_tools(
        tools, parallel_tool_calls=False
    )
    agent = create_react_agent(model, tools, prompt=system_prompt)

    # 4) A real, interactive test flow on a real app — the MODEL decides the steps.
    task = (
        f"Go to {SITE}. Add two todos: 'Write Playwright tests' and 'Ship feature'. "
        "Then tell me exactly how many items the footer says are left, and list the "
        "todo texts you see. Be concise."
    )
    print(f"\n[task] {task}\n")
    result = await agent.ainvoke({"messages": [{"role": "user", "content": task}]})

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
