"""
LESSON 3 — CONDITIONAL EDGES (the `if`) and LOOPS (the `while`).

This is the WHOLE reason LangGraph exists instead of a plain LangChain chain.
A chain is a straight line. A graph can branch and go BACKWARDS.

Scenario (no LLM, so it's free and fast): we "attempt" a task that randomly
fails. On failure we LOOP BACK and retry, up to 3 times, then give up.
That retry-loop shape is exactly what you'd add to agent.py for flaky tests.

Run:
    python learn/03_router_and_loop.py     # run it a few times, outcomes vary

What to notice:
  - should_retry() is a ROUTER: it returns a STRING KEY, not state.
  - add_conditional_edges maps those keys -> next node.
  - The edge "retry" -> "attempt" creates a CYCLE. Chains can't do this.
"""

import random
from typing import TypedDict, Literal
from langgraph.graph import START, END, StateGraph


class State(TypedDict):
    attempts: int
    succeeded: bool
    max_attempts: int


def attempt(state: State) -> dict:
    n = state["attempts"] + 1
    ok = random.random() < 0.4          # 40% chance of success each try
    print(f"[attempt] try #{n} -> {'SUCCESS' if ok else 'fail'}")
    return {"attempts": n, "succeeded": ok}


# ROUTER: look at state, decide the next hop. Returns one of the literal keys.
def should_retry(state: State) -> Literal["retry", "stop"]:
    if state["succeeded"]:
        return "stop"
    if state["attempts"] >= state["max_attempts"]:
        print("[router] out of attempts, giving up")
        return "stop"
    print("[router] failed but attempts remain -> looping back")
    return "retry"


g = StateGraph(State)
g.add_node("attempt", attempt)
g.add_edge(START, "attempt")

# The conditional edge: after `attempt`, run should_retry(); its return value
# is looked up in this map to pick the next node.
g.add_conditional_edges("attempt", should_retry, {
    "retry": "attempt",   # <-- LOOP: go back to attempt
    "stop": END,
})
app = g.compile()

final = app.invoke({"attempts": 0, "succeeded": False, "max_attempts": 3})
print("\n=== FINAL ===", final)
