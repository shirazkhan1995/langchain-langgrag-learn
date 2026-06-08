"""
OpenAPI -> Pytest Agent, v2 — the "production-shaped" version.

agent.py is the SIMPLE spine (5 nodes, straight line + one branch). This file
adds the two things an interviewer will probe for, and that the JD implies:

  1) A RETRY LOOP. After the LLM writes tests we VALIDATE the code (does it even
     parse? does it contain tests?). If not, we loop back to generate_tests and
     feed the error back as a hint — up to MAX_GEN_ATTEMPTS. This is "self-heal".

  2) HUMAN-IN-THE-LOOP. We NEVER auto-execute LLM-generated code. Before
     run_tests, the graph PAUSES (interrupt) and shows a human the code for
     approval. This needs a checkpointer so the graph can be paused & resumed.

Talk-track: "I started simple (agent.py), then added complexity only where it
earns its place — a self-healing retry edge, and a human gate before executing
generated code. I don't let an LLM run arbitrary code unsupervised."

Run (interactive):
    python agent_v2.py petstore_mini.json
    # it will print the generated tests and ask: Approve? [y/N]

Run (non-interactive, auto-approve, for a quick smoke test):
    echo y | python agent_v2.py petstore_mini.json

New concepts vs agent.py:
    - interrupt()  : pause the graph, hand control back to the caller
    - Command(resume=...) : resume the paused graph with the human's answer
    - checkpointer : persists state between pause and resume (thread_id keyed)
"""

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal, TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

LLM = init_chat_model("openai:gpt-4o", temperature=0)
MAX_GEN_ATTEMPTS = 2


# ---------- structured output schemas ----------
class GeneratedTests(BaseModel):
    pytest_code: str = Field(description="Complete runnable pytest file, no markdown fences")
    rationale: str = Field(description="One sentence on coverage choices")


class FailureAnalysis(BaseModel):
    classification: Literal["real_bug", "flake", "environment", "spec_mismatch"]
    root_cause: str
    suggested_fix: str


# ---------- graph state ----------
class AgentState(TypedDict):
    spec_path: str
    endpoints: list[dict]
    pytest_code: str
    gen_attempts: int
    validation_error: str   # empty string means "valid"
    approved: bool
    test_output: str
    test_failed: bool
    analysis: dict


# ---------- nodes ----------
def parse_spec(state: AgentState) -> dict:
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
    """LLM node. On a retry, we append the previous validation error as feedback."""
    attempt = state.get("gen_attempts", 0) + 1
    sys_prompt = (
        "You are a senior SDET. Generate a single pytest file using `requests`. "
        "For each endpoint include: one happy-path test, one boundary/invalid-input "
        "test, and one expected-error test. Return code only via the schema."
    )
    user = f"Endpoints:\n{json.dumps(state['endpoints'], indent=2)}"
    # Self-healing: if the last attempt produced broken code, tell the model.
    if state.get("validation_error"):
        user += (
            f"\n\nYour PREVIOUS attempt was rejected by a validator:\n"
            f"{state['validation_error']}\nFix it and return valid Python."
        )
    result = LLM.with_structured_output(GeneratedTests).invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=user),
    ])
    print(f"[generate_tests] attempt #{attempt}: {result.rationale}")
    return {"pytest_code": result.pytest_code, "gen_attempts": attempt}


def validate_code(state: AgentState) -> dict:
    """Deterministic guardrail: does the generated code parse and contain tests?"""
    code = state["pytest_code"]
    try:
        ast.parse(code)                       # raises SyntaxError if invalid Python
    except SyntaxError as e:
        print(f"[validate_code] INVALID: {e}")
        return {"validation_error": f"SyntaxError: {e}"}
    if "def test_" not in code:
        print("[validate_code] INVALID: no test functions found")
        return {"validation_error": "No `def test_...` functions were generated."}
    print("[validate_code] OK — code parses and has tests")
    return {"validation_error": ""}


def route_after_validate(state: AgentState) -> Literal["regenerate", "gate"]:
    """Retry loop: bad code + attempts left -> regenerate; else proceed to human."""
    if state["validation_error"] and state["gen_attempts"] < MAX_GEN_ATTEMPTS:
        print("[router] validation failed -> looping back to generate_tests")
        return "regenerate"
    return "gate"


def human_gate(state: AgentState) -> dict:
    """HUMAN-IN-THE-LOOP. Pause here; the caller decides whether to execute."""
    decision = interrupt({
        "reason": "About to EXECUTE LLM-generated test code. Approve?",
        "code": state["pytest_code"],
    })
    # On resume, `decision` is whatever the caller passed to Command(resume=...).
    approved = bool(decision)
    print(f"[human_gate] human approved = {approved}")
    return {"approved": approved}


def route_after_gate(state: AgentState) -> Literal["run", "abort"]:
    return "run" if state["approved"] else "abort"


def run_tests(state: AgentState) -> dict:
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
    result = LLM.with_structured_output(FailureAnalysis).invoke([
        SystemMessage(content=(
            "You triage failing API tests. Classify the failure as one of: "
            "real_bug, flake, environment, spec_mismatch. Be specific."
        )),
        HumanMessage(content=f"Pytest output:\n{state['test_output'][:4000]}"),
    ])
    print(f"[analyze_failure] {result.classification}: {result.root_cause}")
    return {"analysis": result.model_dump()}


def should_analyze(state: AgentState) -> Literal["analyze", "done"]:
    return "analyze" if state["test_failed"] else "done"


# ---------- wire the graph ----------
def build_graph():
    g = StateGraph(AgentState)
    g.add_node("parse_spec", parse_spec)
    g.add_node("generate_tests", generate_tests)
    g.add_node("validate_code", validate_code)
    g.add_node("human_gate", human_gate)
    g.add_node("run_tests", run_tests)
    g.add_node("analyze_failure", analyze_failure)

    g.add_edge(START, "parse_spec")
    g.add_edge("parse_spec", "generate_tests")
    g.add_edge("generate_tests", "validate_code")
    # Retry edge: validate -> (regenerate | gate)
    g.add_conditional_edges("validate_code", route_after_validate,
                            {"regenerate": "generate_tests", "gate": "human_gate"})
    # Human gate -> (run | abort)
    g.add_conditional_edges("human_gate", route_after_gate,
                            {"run": "run_tests", "abort": END})
    g.add_conditional_edges("run_tests", should_analyze,
                            {"analyze": "analyze_failure", "done": END})
    g.add_edge("analyze_failure", END)

    # A checkpointer is REQUIRED for interrupt()/resume to work.
    return g.compile(checkpointer=InMemorySaver())


if __name__ == "__main__":
    spec_path = sys.argv[1] if len(sys.argv) > 1 else "petstore_mini.json"
    app = build_graph()
    # thread_id ties the paused run to its resume. Any stable string works.
    config = {"configurable": {"thread_id": "demo-run-1"}}

    state = app.invoke(
        {"spec_path": spec_path, "gen_attempts": 0, "validation_error": "", "approved": False},
        config,
    )

    # The graph pauses at human_gate; invoke() returns with an "__interrupt__" key.
    while "__interrupt__" in state:
        payload = state["__interrupt__"][0].value
        print("\n=== HUMAN GATE ===")
        print(payload["reason"])
        print("\n--- generated code ---\n")
        print(payload["code"])
        answer = input("\nApprove running these tests? [y/N]: ").strip().lower()
        # Resume the graph from where it paused, feeding back the human's decision.
        state = app.invoke(Command(resume=(answer == "y")), config)

    if state.get("approved") is False and "test_output" not in state:
        print("\n[aborted] Human rejected execution. No tests were run.")
    else:
        print("\n=== GENERATED TESTS ===\n")
        print(state["pytest_code"])
        if state.get("analysis"):
            print("\n=== FAILURE ANALYSIS ===\n")
            print(json.dumps(state["analysis"], indent=2))
