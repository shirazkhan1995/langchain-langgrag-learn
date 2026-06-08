"""
LESSON 2 — STATE and NODES, with NO LLM at all.

The single most important thing to internalize: a LangGraph node is just a
function that takes the state and RETURNS A PARTIAL DICT. LangGraph merges that
dict into the running state and hands it to the next node. No magic.

Run:
    python learn/02_state_and_graph.py

What to notice:
  - We never mention an LLM. A graph is just orchestrated plain functions.
  - Each node returns ONLY the keys it changed. LangGraph merges, doesn't replace.
  - Print statements show the state growing as it flows through the nodes.
"""

from typing import TypedDict
from langgraph.graph import START, END, StateGraph


# 1) STATE: the shared "whiteboard" every node can read and write.
class State(TypedDict):
    raw_text: str
    word_count: int
    shout: str


# 2) NODES: each is `state -> partial dict`.
def count_words(state: State) -> dict:
    n = len(state["raw_text"].split())
    print(f"[count_words] saw {n} words")
    return {"word_count": n}          # <-- only returns the key it produced


def make_shout(state: State) -> dict:
    out = state["raw_text"].upper() + "!!!"
    print(f"[make_shout] -> {out}")
    return {"shout": out}             # <-- merged in alongside word_count


# 3) WIRE the graph: START -> count_words -> make_shout -> END
g = StateGraph(State)
g.add_node("count_words", count_words)
g.add_node("make_shout", make_shout)
g.add_edge(START, "count_words")
g.add_edge("count_words", "make_shout")
g.add_edge("make_shout", END)
app = g.compile()

# 4) RUN: pass the INITIAL state. Get the FINAL merged state back.
final = app.invoke({"raw_text": "langgraph is just functions and a dict"})

print("\n=== FINAL STATE ===")
for k, v in final.items():
    print(f"  {k}: {v!r}")
print("\nNotice: final state has raw_text + word_count + shout — accumulated.")
