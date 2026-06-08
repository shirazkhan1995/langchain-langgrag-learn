"""
LESSON 6 — A TRUE AGENT (tool-calling loop). THE most likely interview probe.

THE DISTINCTION YOU MUST NAIL:
  - WORKFLOW (your agent.py): YOU hardcoded the path parse->generate->run->analyze.
    The LLM fills in steps but never decides the route. Predictable, cheap, safe.
  - AGENT (this file): the LLM DECIDES which tool to call next, in a LOOP, until it
    has enough to answer. Control flow is chosen by the model at runtime.

Rule of thumb to say out loud: "Use a workflow when the steps are known; use an
agent when the path depends on inputs you can't predict. Don't pay for agency you
don't need." (That's the Anthropic 'Building Effective Agents' line.)

How tool-calling actually works under the hood (say this if asked):
  1. You bind tool SCHEMAS to the model (llm.bind_tools([...])).
  2. The model doesn't run anything — it RETURNS a structured `tool_calls` list
     (tool name + args) when it wants one.
  3. YOUR code executes the tool and feeds the result back as a ToolMessage.
  4. The model sees the result and either calls another tool or writes the answer.
  That 2->3->4 cycle is the ReAct loop. This graph implements it explicitly.

Run:
    python learn/06_tool_calling_agent.py
"""

from typing import Annotated, Literal, TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


# ---------- TOOLS: plain Python functions the LLM is allowed to call ----------
# The docstring is NOT a comment — it's sent to the model as the tool's description,
# so it must clearly say WHEN to use the tool (same idea as Field(description=...)).
@tool
def list_endpoints() -> str:
    """List every available API endpoint by method and path."""
    return "GET /pets, POST /pets, GET /pets/{petId}"


@tool
def get_endpoint_schema(endpoint: str) -> str:
    """Return required fields/params for an endpoint, e.g. endpoint='POST /pets'."""
    schemas = {
        "POST /pets": "JSON body: name (str, required), species (str, required: dog|cat|bird)",
        "GET /pets": "query param: limit (int, optional, max 100)",
        "GET /pets/{petId}": "path param: petId (int, required)",
    }
    return schemas.get(endpoint, f"No schema on file for {endpoint}")


@tool
def check_endpoint_health(endpoint: str) -> str:
    """Return the current live HTTP status of an endpoint, e.g. 'POST /pets'."""
    health = {
        "POST /pets": "503 Service Unavailable",   # <-- the agent should discover this
        "GET /pets": "200 OK",
        "GET /pets/{petId}": "200 OK",
    }
    return health.get(endpoint, "404 unknown endpoint")


TOOLS = [list_endpoints, get_endpoint_schema, check_endpoint_health]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}

# bind_tools attaches the tool SCHEMAS so the model knows what it can call.
llm = init_chat_model("openai:gpt-4o", temperature=0).bind_tools(TOOLS)


# ---------- STATE: a running transcript. add_messages APPENDS, never overwrites --
class State(TypedDict):
    messages: Annotated[list, add_messages]   # reducer: new msgs get appended


# ---------- NODES ----------
def agent(state: State) -> dict:
    """The 'brain': the model looks at the transcript and either calls a tool or answers."""
    response = llm.invoke(state["messages"])
    if response.tool_calls:
        names = [c["name"] for c in response.tool_calls]
        print(f"[agent] model wants to call: {names}")
    else:
        print("[agent] model is ready to answer (no more tools)")
    return {"messages": [response]}


def tools(state: State) -> dict:
    """The 'hands': execute whatever tools the model asked for, return their outputs."""
    last = state["messages"][-1]
    outputs = []
    for call in last.tool_calls:
        print(f"   [tool] {call['name']}({call['args']})")
        result = TOOLS_BY_NAME[call["name"]].invoke(call["args"])
        # ToolMessage ties the result back to the specific tool_call_id the model issued.
        outputs.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    return {"messages": outputs}


def should_continue(state: State) -> Literal["tools", "done"]:
    """If the model emitted tool_calls, run them; otherwise we have the final answer."""
    return "tools" if state["messages"][-1].tool_calls else "done"


# ---------- WIRE: agent <-> tools loop (this cycle IS the agent) ----------
g = StateGraph(State)
g.add_node("agent", agent)
g.add_node("tools", tools)
g.add_edge(START, "agent")
g.add_conditional_edges("agent", should_continue, {"tools": "tools", "done": END})
g.add_edge("tools", "agent")        # <-- loop back so the model sees tool results
app = g.compile()


if __name__ == "__main__":
    # A question that needs SEVERAL tools, in an order the MODEL chooses:
    question = (
        "I want to create a new pet via the API. Which endpoint do I use, what "
        "fields does it require, and is that endpoint actually working right now?"
    )
    print(f"USER: {question}\n")
    final = app.invoke({"messages": [
        SystemMessage(content="You are an API assistant. Use the tools to answer precisely."),
        HumanMessage(content=question),
    ]})
    print("\n=== FINAL ANSWER ===\n")
    print(final["messages"][-1].content)
    print("\nNotice: nobody hardcoded 'call schema then health'. The MODEL sequenced it.")
    print("THAT autonomy is what makes this an agent, not a workflow.")
