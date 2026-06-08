"""
OpenAPI -> Pytest Agent (LangGraph)

Run:  python agent.py specs/petstore_mini.json

The graph has 4 working nodes + 1 router:
  parse_spec      (deterministic) : OpenAPI JSON -> list of endpoint summaries
  generate_tests  (LLM)           : endpoints -> pytest source code (structured)
  run_tests       (deterministic) : execute pytest in a subprocess, capture output
  analyze_failure (LLM)           : failing output -> classification + root cause
  should_analyze  (router)        : branch on whether there were failures

Why this shape: only generate/analyze are LLM calls. Everything an ordinary
program does reliably (parsing, running a subprocess) stays deterministic.
That is the whole "don't make it agentic where it doesn't need to be" point.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

# --- model: swap to "openai:gpt-4o" if you prefer; both work via init_chat_model ---
LLM = init_chat_model("openai:gpt-4o", temperature=0)


# ---------- structured output schemas ----------
class GeneratedTests(BaseModel):
    """The LLM returns this, not free-form text, so the result is parseable."""
    pytest_code: str = Field(description="Complete runnable pytest file, no markdown fences")
    rationale: str = Field(description="One sentence on coverage choices (happy path, boundary, error)")


class FailureAnalysis(BaseModel):
    classification: Literal["real_bug", "flake", "environment", "spec_mismatch"]
    root_cause: str = Field(description="Concise root cause hypothesis")
    suggested_fix: str = Field(description="What a human should do next")


# ---------- graph state ----------
class AgentState(TypedDict):
    spec_path: str
    endpoints: list[dict]
    pytest_code: str
    test_output: str
    test_failed: bool
    analysis: dict


# ---------- nodes ----------
def parse_spec(state: AgentState) -> dict:
    """Deterministic: flatten the OpenAPI paths into a compact endpoint list."""
    spec = json.loads(Path(state["spec_path"]).read_text())
    base_url = (spec.get("servers") or [{}])[0].get("url", "")
    endpoints = []
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            endpoints.append({
                "method": method.upper(),
                "path": path,
                "operationId": op.get("operationId"),
                "summary": op.get("summary"),
                "parameters": op.get("parameters", []),
                "requestBody": op.get("requestBody", {}),
                "responses": list(op.get("responses", {}).keys()),
            })
    print(f"[parse_spec] base_url={base_url} endpoints={len(endpoints)}")
    return {"endpoints": endpoints}


def generate_tests(state: AgentState) -> dict:
    """LLM node: turn the endpoint list into a pytest file with structured output."""
    sys_prompt = (
        "You are a senior SDET. Generate a single pytest file using `requests`. "
        "For each endpoint include: one happy-path test, one boundary/invalid-input "
        "test, and one expected-error test. Use clear test names. "
        "Return the code only via the structured schema."
    )
    user = json.dumps(state["endpoints"], indent=2)
    structured = LLM.with_structured_output(GeneratedTests)
    result = structured.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=f"Endpoints:\n{user}"),
    ])
    print(f"[generate_tests] rationale: {result.rationale}")
    return {"pytest_code": result.pytest_code}


def run_tests(state: AgentState) -> dict:
    """Deterministic: write the generated file and run pytest, capturing output."""
    with tempfile.TemporaryDirectory() as d:
        test_file = Path(d) / "test_generated.py"
        test_file.write_text(state["pytest_code"])
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-q"],
            capture_output=True, text=True, timeout=120,
        )
    output = proc.stdout + proc.stderr
    failed = proc.returncode != 0
    print(f"[run_tests] returncode={proc.returncode} failed={failed}")
    return {"test_output": output, "test_failed": failed}


def analyze_failure(state: AgentState) -> dict:
    """LLM node: classify the failure. This is FlakyGuard applied to a fresh suite."""
    structured = LLM.with_structured_output(FailureAnalysis)
    result = structured.invoke([
        SystemMessage(content=(
            "You triage failing API tests. Classify the failure as one of: "
            "real_bug, flake, environment, spec_mismatch. Be specific."
        )),
        HumanMessage(content=f"Pytest output:\n{state['test_output'][:4000]}"),
    ])
    print(f"[analyze_failure] {result.classification}: {result.root_cause}")
    return {"analysis": result.model_dump()}


def should_analyze(state: AgentState) -> Literal["analyze", "done"]:
    """Conditional edge: only spend an LLM call on analysis if something failed."""
    return "analyze" if state["test_failed"] else "done"


# ---------- wire the graph ----------
def build_graph():
    g = StateGraph(AgentState)
    g.add_node("parse_spec", parse_spec)
    g.add_node("generate_tests", generate_tests)
    g.add_node("run_tests", run_tests)
    g.add_node("analyze_failure", analyze_failure)

    g.add_edge(START, "parse_spec")
    g.add_edge("parse_spec", "generate_tests")
    g.add_edge("generate_tests", "run_tests")
    g.add_conditional_edges("run_tests", should_analyze,
                            {"analyze": "analyze_failure", "done": END})
    g.add_edge("analyze_failure", END)
    return g.compile()


if __name__ == "__main__":
    spec_path = sys.argv[1] if len(sys.argv) > 1 else "specs/petstore_mini.json"
    app = build_graph()
    final = app.invoke({"spec_path": spec_path})
    print("\n=== GENERATED TESTS ===\n")
    print(final["pytest_code"])
    if final.get("analysis"):
        print("\n=== FAILURE ANALYSIS ===\n")
        print(json.dumps(final["analysis"], indent=2))
