"""
LESSON 1 — The LLM, and why we force STRUCTURED output.

Run:
    cd "/Volumes/T7 new/langchain-langgrag-learn"
    source .venv/bin/activate
    export OPENAI_API_KEY=sk-...
    python learn/01_llm_basics.py

What to notice:
  - init_chat_model gives you ONE interface over any provider (openai/anthropic).
  - A raw .invoke() returns free-form text — a STRING. Hard to use in a program.
  - .with_structured_output(Schema) makes the model fill a Pydantic object.
    Now the result has typed fields you can rely on (result.severity, etc.).
    This is THE trick that lets an LLM be a reliable step in automation.
"""

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from typing import Literal

# One line, swap the string to change provider. temperature=0 => deterministic-ish.
llm = init_chat_model("openai:gpt-4o", temperature=0)

# ---- Part A: raw text output -------------------------------------------------
print("=== RAW TEXT ===")
resp = llm.invoke([
    SystemMessage(content="You are a terse QA engineer."),
    HumanMessage(content="A login API returned 500 on valid creds. One sentence: what is this?"),
])
print(type(resp.content), "->", resp.content)
# Problem: resp.content is just a string. To branch on it in code you'd have to
# parse English. Fragile.

# ---- Part B: structured output ----------------------------------------------
class BugReport(BaseModel):
    severity: Literal["low", "medium", "high", "critical"]
    is_real_bug: bool = Field(description="True if a genuine defect, not env/flake")
    summary: str

print("\n=== STRUCTURED ===")
structured_llm = llm.with_structured_output(BugReport)
report: BugReport = structured_llm.invoke([
    SystemMessage(content="You triage API test failures."),
    HumanMessage(content="A login API returned 500 on valid creds."),
])
print("severity:    ", report.severity)      # typed field, not a string blob
print("is_real_bug: ", report.is_real_bug)   # a real bool you can `if` on
print("summary:     ", report.summary)
print("\nNow `if report.is_real_bug:` works. THAT is why agent.py uses Pydantic.")
