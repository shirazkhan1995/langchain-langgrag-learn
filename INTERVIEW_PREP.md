# Interview Prep — GenAI SDET II (LangGraph · RAG · Agents)

A self-contained reference distilled from a hands-on prep session. Everything here
is backed by runnable code in this repo. Read this, run the `learn/` ladder, then
rehearse the talking points out loud.

**Scored topics (from the interviewer):** AI Agent Frameworks 33% · LLM RAG 33% ·
Playwright 34% (prepared separately). This doc covers the first two.

---

## 0. How to run everything (any machine)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...          # the code uses openai:gpt-4o

# the learning ladder (run in order):
python learn/02_state_and_graph.py    # no key needed
python learn/03_router_and_loop.py    # no key needed
python learn/01_llm_basics.py
python learn/04_rag_mini.py
python learn/05_rag_over_logs.py
python learn/06_tool_calling_agent.py
python learn/07_rag_retrieval_and_eval.py

# the project agents:
python agent.py petstore_mini.json        # simple workflow
python agent_v2.py petstore_mini.json     # + retry loop + human-in-the-loop gate
```

The petstore URL is fake, so the generated tests "fail" on purpose — that exercises
the failure-analysis branch and gives you a live demo of AI-driven debugging.

---

## 1. Mental model: LangChain vs LangGraph

- **LangChain** = the *toolbox*: model wrappers (`init_chat_model`), message types
  (`SystemMessage`/`HumanMessage`/`ToolMessage`), structured output, embeddings,
  vector stores, retrievers. Best for **linear** flows: input → LLM → output.
- **LangGraph** = the *orchestrator*: a **stateful graph** of steps that can
  **branch, loop, and pause for a human**. Reach for it the moment the flow has an
  "if this failed, go back / go analyze" shape.

> Your `agent.py` is LangGraph wiring together LangChain pieces.

### The 5 LangGraph primitives (all of LangGraph is these)

1. **State** — a `TypedDict` that flows through the graph. Nodes return a *partial*
   dict; LangGraph **merges** it in (it doesn't replace the whole state).
2. **Node** — a plain function `state -> dict`. Some call an LLM, some don't.
3. **Edge** — `A → B`, "after A, run B."
4. **Conditional edge** — a *router* function reads state and returns a **string key**
   naming the next node. This is the `if`.
5. **Compile + invoke** — `build_graph()` returns a runnable; `.invoke(initial_state)`
   runs it from START to END.

**Reducers:** a state field can have a reducer that controls how updates merge.
`Annotated[list, add_messages]` means new messages get **appended** to the
transcript instead of overwriting it (used by the agent in `learn/06`).

---

## 2. THE distinction interviewers probe: Workflow vs Agent

| | **Workflow** (`agent.py`) | **Agent** (`learn/06`) |
|---|---|---|
| Who decides the control flow? | **You did, in code** (parse→generate→run→analyze) | **The LLM**, at runtime, in a loop |
| Path | Fixed graph | Dynamic — model-directed |
| LLM's role | Fills in steps | Drives the whole process |
| When to use | The steps are known up front | The path depends on inputs you can't predict |

**Say this:** *"Use a workflow when the steps are known; use an agent when the path
depends on inputs you can't predict. Don't pay for agency you don't need."*
(Anthropic, *Building Effective Agents*.) Your project is deliberately a workflow
with one conditional — that's correct engineering, not a limitation.

---

## 3. Structured output (why every LLM step uses Pydantic)

A raw `llm.invoke()` returns a **string** — fragile to parse. `.with_structured_output(Schema)`
serializes a Pydantic model into a JSON Schema, sends it to the model, and forces
the model to fill it. You get back a typed object you can branch on.

```python
class FailureAnalysis(BaseModel):
    classification: Literal["real_bug","flake","environment","spec_mismatch"]
    root_cause: str = Field(description="Concise root cause hypothesis")
```

- `Literal[...]` = a TypeScript-style union; Pydantic enforces it at runtime.
- `Field(description=...)` is **not a comment** — the description is transmitted in
  the JSON Schema and acts as inline instruction to the model. Use it on every
  ambiguous field. (`Field` also does constraints/defaults: `min_length`, `ge`, `default`.)
- Mental model for TS devs: a Pydantic `BaseModel` ≈ a `zod` schema used as both an
  interface *and* a runtime validator.

This is what makes an LLM a **reliable step in automation** rather than a black box.

---

## 4. Tool calling (how an agent actually "uses tools")

The model never executes anything itself. The loop:

1. You bind tool **schemas**: `llm.bind_tools([...])`. A tool is a Python function;
   its **docstring** is sent as the tool description (says *when* to use it).
2. The model returns a structured `tool_calls` list (tool name + args) when it wants one.
3. **Your code** executes the tool and feeds the result back as a `ToolMessage`
   (tied to the `tool_call_id` the model issued).
4. The model sees the result and either calls another tool or writes the final answer.

Steps 2→3→4 repeated = the **ReAct loop**. In `learn/06` this is an explicit graph:
`agent` node ↔ `tools` node, looping until the model stops requesting tools.
Models can also request **several tools in parallel** in one turn.

---

## 5. Retry + Human-in-the-Loop (`agent_v2.py`)

The "production-shaped" version adds two things interviewers love:

- **Self-healing retry edge:** after `generate_tests`, a deterministic `validate_code`
  node checks the code parses (`ast.parse`) and contains `def test_`. If not, it
  loops back to `generate_tests` with the error as feedback (bounded by `MAX_GEN_ATTEMPTS`).
- **Human-in-the-loop gate:** before executing LLM-generated code, the graph
  **pauses** with `interrupt()` and waits for approval. This requires a
  **checkpointer** (`InMemorySaver`) so the run can pause and resume; you resume by
  calling `app.invoke(Command(resume=decision), config)` with a stable `thread_id`.

**Say this:** *"I never auto-execute LLM-generated code — there's a human gate. And
the generation step self-heals via a validation retry loop. I start simple and add
agentic complexity only where it earns its place."*

---

## 6. RAG (Retrieval-Augmented Generation)

**What it is:** before answering, fetch relevant text and put it in the prompt, so
the model answers from *your* corpus instead of its memory. **No fine-tuning.**

**The pipeline:** load → **chunk** → **embed** → **store** (vector DB) → **retrieve**
(similarity search) → **generate** (stuff retrieved chunks into the prompt).

### Chunking (`learn/05`)
- `chunk_size` = max chars/chunk; `chunk_overlap` = chars repeated across boundaries
  so a fact split across two chunks isn't lost.
- Trade-off: **small chunks** → precise retrieval but lose context; **big chunks** →
  more context but more tokens and diluted relevance. Start ~500–1000 chars, 10–20%
  overlap, then tune by evaluation.

### Retrieval strategies (`learn/07`)
- **Similarity top-k (with scores):** the score lets you threshold ("if best score
  < X, say I don't know"). Tuning `k` is a recall/precision trade-off.
- **MMR (Maximal Marginal Relevance):** relevant **and** diverse results — avoids 3
  near-duplicate chunks.
- **Hybrid search:** combine BM25 keyword + vector search; catches exact terms
  (error codes, IDs) embeddings miss.
- **Re-ranking:** over-fetch (k=20), then a cross-encoder re-scores the top hits.
- **Metadata filtering:** restrict retrieval by tags (service, env, date).

### Embeddings & vector stores
- Embedding models: `text-embedding-3-small` (cheap/fast, fine for most) vs `-large`
  (more accurate for nuanced search).
- Stores: **InMemory** (demos/tests) · **FAISS/Chroma** (local, free) ·
  **pgvector/Pinecone/Weaviate** (production: persistent, scalable, filtered search).

### Evaluation — the differentiator (`learn/07`)
- **Groundedness / faithfulness** (the top metric): is every claim in the answer
  supported by the retrieved context? Catches hallucination. Implemented here as an
  **LLM-as-judge** that returns `grounded: bool` + `unsupported_claims` — and it
  correctly flags a planted lie in the demo.
- Other metrics to name: **answer relevance**, **context precision/recall**.
- Tools to name: **RAGAS**, **LangSmith** evals.
- Failure modes: bad chunking, "lost in the middle," retrieval miss → hallucination,
  stale index.

### RAG vs alternatives (when each wins)
- **RAG:** big/changing corpus; need citations/freshness; cheap to update (re-index).
- **Fine-tuning:** you need new *behavior/style/format*, not new facts.
- **Long-context (paste it all in):** the doc fits in context and you always need all
  of it. RAG earns its keep when the corpus is large.

### Agentic RAG (`learn/07` Part C)
Plain RAG *always* retrieves. **Agentic RAG** makes retrieval a **tool** the agent may
or may not call (and can call repeatedly, refining the query). It's the intersection
of both scored buckets — a strong thing to demo.

---

## 7. File-by-file (what each proves)

| File | Bucket | Teaches |
|---|---|---|
| `learn/01_llm_basics.py` | Agents | LLM call + structured output / `Field` |
| `learn/02_state_and_graph.py` | Agents | State, nodes, edges (no LLM) |
| `learn/03_router_and_loop.py` | Agents | Conditional edges + loops |
| `learn/04_rag_mini.py` | RAG | RAG in 3 steps |
| `learn/05_rag_over_logs.py` | RAG | Chunking + vector-store trade-offs (log triage) |
| `learn/06_tool_calling_agent.py` | Agents | **True agent**: ReAct tool-calling loop |
| `learn/07_rag_retrieval_and_eval.py` | RAG | Retrieval depth + **eval** + agentic RAG |
| `agent.py` | Agents | OpenAPI → pytest **workflow** |
| `agent_v2.py` | Agents | + retry loop + **human-in-the-loop** gate |

---

## 8. Interview Q&A checklist (rehearse out loud)

**AI Agent Frameworks**
- [ ] LangChain vs LangGraph (toolbox vs orchestrator)
- [ ] Workflow vs agent — who controls the flow, and when to use each
- [ ] The 5 primitives; state merging; the `add_messages` reducer
- [ ] How tool-calling works (model emits `tool_calls` → your code runs them → `ToolMessage`)
- [ ] The ReAct loop; HITL via `interrupt()` + checkpointer
- [ ] When **NOT** to use an agent (cost, latency, reliability → prefer a workflow)

**LLM RAG**
- [ ] The pipeline: load → chunk → embed → store → retrieve → generate
- [ ] Chunking trade-offs (size/overlap)
- [ ] Retrieval strategies (top-k, MMR, hybrid, re-ranking, metadata filtering)
- [ ] RAG vs fine-tuning vs long-context
- [ ] **Evaluation**: groundedness/faithfulness, context recall/precision; RAGAS/LangSmith
- [ ] Failure modes (bad chunking, lost-in-the-middle, retrieval miss → hallucination)

**Prep ratio:** you've done the hands-on; the interview scores what you can *explain*.
For the final days aim ~25% hands-on (run the lessons, tweak one) / ~75% explaining
out loud. Hands-on is your credibility anchor ("I built X, here's what happened");
articulation is what's graded.

---

## 9. Resources

- LangGraph low-level concepts: https://langchain-ai.github.io/langgraph/concepts/low_level/
- Structured output: https://python.langchain.com/docs/concepts/structured_outputs/
- RAG tutorial: https://python.langchain.com/docs/tutorials/rag/
- Anthropic, *Building Effective Agents*: https://www.anthropic.com/research/building-effective-agents
