# OpenAPI → Pytest Agent

A LangGraph agent that ingests an OpenAPI/Swagger spec, generates `pytest` API test
cases for each endpoint, (optionally) executes them, and analyzes failures with an LLM.

This maps directly to the Panasonic JD bullets:
- "OpenAPI-to-test-generation agents"
- "AI-assisted test case generation and execution"
- "AI-driven debugging"
- "LangChain / LangGraph"

## Architecture (the graph)

```
        ┌──────────────┐
        │  parse_spec  │  deterministic Python — NOT an LLM call
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │ generate_tests│  LLM node: spec → pytest code (structured output)
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │  run_tests   │  deterministic — subprocess pytest, capture output
        └──────┬───────┘
               ▼
        ┌──────────────┐      no failures
        │ should_analyze├───────────────► END
        └──────┬───────┘
               │ failures
               ▼
        ┌──────────────┐
        │analyze_failure│ LLM node: classify (real bug / flake / spec mismatch)
        └──────┬───────┘
               ▼
              END
```

Key design point for the interview: **only two of five nodes are LLM calls.**
Spec parsing and test execution are deterministic code. That's the Anthropic
"start simple, add agentic complexity only where it earns its place" principle —
you don't ask an LLM to do what `json.load` and `subprocess` do reliably.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # or OPENAI_API_KEY
python agent.py specs/petstore_mini.json
```

## What to say when they ask "walk me through this"

1. State + nodes + conditional edge — the LangGraph mental model.
2. Why parse/run are deterministic and generate/analyze are LLM (judgment).
3. Structured output via Pydantic so generated tests are parseable, not free text.
4. The failure-analysis node is the FlakyGuard idea applied to a fresh suite:
   classify each failure as real-bug / flake / environment / spec-mismatch.
5. Where it would break at scale and what you'd add: cost caps, retry policy,
   human-in-the-loop gate before executing generated code, observability on LLM calls.
