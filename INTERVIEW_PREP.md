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

## 2.5 Core components of an agent

An agent is an LLM that runs in a **loop**, choosing its own actions until a goal is
met. Six components — each mapped to this repo's code:

1. **Model (reasoning core / "brain")** — the LLM that decides *what to do next*. It
   reasons and emits decisions; it never executes anything itself. → `init_chat_model(...).bind_tools(...)`.
2. **Instructions (policy / system prompt)** — role, constraints, and *when* to use
   which tool. Shapes behaviour without retraining. → the `SystemMessage`.
3. **Tools (capabilities / actions)** — functions it calls to fetch info or affect the
   world; the model sees each tool's docstring + arg schema. → `@tool` functions in `learn/06`.
4. **Memory** — *short-term*: the running transcript incl. tool results, so the model
   sees the whole trajectory (→ `Annotated[list, add_messages]`); *long-term*:
   persistence across sessions via a checkpointer (→ `InMemorySaver` in `agent_v2.py`)
   or a vector store of past interactions (= RAG applied to memory).
5. **Orchestration / control loop (engine)** — drives reason → act → observe → repeat,
   and decides *when to stop*. This is the ReAct pattern. → the LangGraph `agent ↔ tools`
   cycle with the `should_continue` router. Without the loop it's one LLM call, not an agent.
6. **Planning / reasoning** — *implicit/interleaved* (ReAct: decide one step at a time,
   reacting to each result — `learn/06`) vs *explicit* (plan-and-execute: write the full
   plan upfront, then run it — better for long tasks, less adaptive).

**Spoken answer:**
> "An agent is an LLM running in a loop that can take actions. Six components: the
> **model** is the reasoning core — it decides but never executes. **Instructions** are
> its policy — role, constraints, when to use which tool. **Tools** are its hands —
> functions exposed via their schemas. **Memory** is short-term (the running message
> history, so it sees the whole trajectory) plus long-term (persistence across sessions
> via a checkpointer or a vector store of past interactions). The **orchestration loop**
> is the engine — reason, act, observe, repeat — and critically decides when to stop.
> And **planning** is how it decomposes the goal, interleaved as in ReAct or as an
> explicit upfront plan. In my agent: gpt-4o with bound tools, Python tool functions,
> append-only message state, a LangGraph agent↔tools loop, and a checkpointer for persistence."

**Likely follow-ups:**
- *How does it decide when to stop?* — "When the model returns no more tool calls. In
  practice also a **max-iteration cap** so a confused agent can't loop forever, and
  sometimes an explicit `finish` tool."
- *What stops infinite loops / runaway cost?* — "Max-iteration guard + per-run
  token/cost budgets. Matters most for tool-calling agents — a reliability *and* cost control."
- *Short-term vs long-term memory?* — "Short-term = the message list for the current
  task, in context. Long-term outlives the session, stored and *retrieved* when relevant
  — essentially RAG over the agent's own history."
- *Where does planning happen in ReAct?* — "Implicit and interleaved — it decides the
  next action after each observation. Plan-and-execute commits to a full plan first."
- *How is this different from a workflow?* — "A workflow's control flow is hardcoded by
  me; an agent's is chosen by the model at runtime via the loop. The loop + tool-choice
  is what makes it an agent."
- *Riskiest component?* — "Tools — that's where it touches real systems. So execution
  stays in my code, and high-risk tools sit behind a human-in-the-loop gate."

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

### Chunking — deep dive (`learn/05`)

**Why chunking exists at all** (say this first if asked):
1. Embedding models have an input limit — you can't embed a 50-page doc as one vector.
2. One vector for a huge doc is a *blurry average* — a "rate limits" query won't match
   sharply against a vector representing an entire manual.
3. You want to retrieve the relevant *piece*, not the whole book, to keep the
   generation prompt focused and cheap.

So a chunk must be three things at once: **small enough to embed**, **specific enough
to match a query sharply**, **self-contained enough to be useful when retrieved alone.**

**The one tension everything orbits:**
- **Too small** → sharp match, but the chunk lacks context to answer; facts get split
  across boundaries.
- **Too big** → rich context, but a blurry embedding (diluted relevance), more tokens,
  and irrelevant text dragged in alongside the answer.

There is **no universal chunk size.** Each strategy below is a different way to
navigate that precision-vs-context trade-off.

**1. Fixed-size** — cut every N chars/tokens, ignoring the text entirely.
  - *Pros:* dead simple, fast, predictable size, no assumptions.
  - *Cons:* splits words/sentences/facts blindly; mixes unrelated topics in one chunk.
    `chunk_overlap` (repeat ~10–20% between neighbours) is the band-aid so a fact
    severed at a boundary still appears whole in one chunk — at the cost of redundancy.
  - *Use when:* truly structureless streams (OCR dumps). Mostly a baseline.

**2. Recursive character splitting** (`RecursiveCharacterTextSplitter`, the default) —
  same size target, but cut at natural seams in priority order: paragraph (`\n\n`) →
  sentence (`. `) → word → raw char. Hits the size budget while cutting at seams, not
  mid-thought.
  - *Pros:* respects language boundaries; same speed/simplicity as fixed-size; good for ~80% of cases.
  - *Cons:* still size-driven not meaning-driven; treats `# Header` as plain text.
  - *Use when:* your **default** for prose — docs, tickets, logs. Start here unless you have a reason not to.

**3. Document-structure-aware** — split on the document's own structure (Markdown
  headers, HTML, code boundaries, JSON keys, OpenAPI endpoints). Each section becomes
  one chunk, with the header stored as **metadata**.
  - *Pros:* chunks align with real semantic units; header metadata enables filtering
    ("search only the Auth section"); near-zero "split a fact in half" risk.
  - *Cons:* needs the doc to *have* structure; a giant section may still need an
    inner size split; useless on raw logs.
  - *Use when:* structured sources — **OpenAPI/Swagger specs**, Markdown/HTML docs,
    source code, Confluence. First choice whenever structure exists.

**4. Semantic chunking** — embed each sentence, cut where similarity between
  consecutive sentences drops sharply (a topic shift), so boundaries match meaning.
  - *Pros:* boundaries match true topic shifts; works on flowing prose with no headers.
  - *Cons:* expensive (embed every sentence just to decide cuts); unpredictable chunk sizes.
  - *Use when:* long, unstructured docs that shift topics mid-paragraph — papers,
    long incident write-ups, transcripts.

**5. Parent-document retrieval (small-to-big)** — the strategy that *resolves* the
  tension instead of compromising: index/search on **small** chunks (sharp matching),
  but return the **larger parent** section to the LLM (rich context).
  - *Pros:* small-chunk precision + large-chunk context simultaneously; kills the
    "retrieved the right line but missed surrounding context" failure.
  - *Cons:* more complex (maintain chunk→parent mapping); more storage.
  - *Use when:* answer quality is critical and docs have a sentence→section hierarchy.

**6. Late chunking** (advanced/bonus) — embed the **whole doc first** with a
  long-context embedder (so every token's vector already "saw" the full document),
  *then* pool token-embeddings per chunk. Each small chunk keeps document-level context
  in its vector — fixes "lost context across boundaries" at the *embedding* level.
  Know it exists; not expected to have built it.

**Decision flow:**
```
Has explicit structure (headers/code/JSON/OpenAPI)? → Structure-aware
Long unstructured prose that shifts topics?         → Semantic
Need sharp retrieval AND full context, quality key? → Parent-document (small-to-big)
Just need a solid default?                          → Recursive, ~500–1000 chars, 10–20% overlap
Truly raw structureless stream?                     → Fixed-size + overlap (last resort)
```

**The two sentences that win the question:**
1. "Chunking navigates one tension — too small and the chunk lacks context, too big
   and the embedding gets blurry and retrieval drags in noise."
2. "There's no universal size; I match the strategy to the document structure, then
   **tune it against retrieval recall and groundedness metrics** — chunking is an
   upstream knob I tune against eval, not a fixed guess."

### Retrieval strategies — deep dive (`learn/07`)

**The basic mechanism (say this first):** embed the *query* (a query is **embedded,
not chunked** — chunking is a document-side concern) into the same vector space as the
documents, then find the nearest chunk vectors by **cosine similarity**. The top-k
nearest become the generation context. Everything below modifies this baseline.

**1. Top-k similarity search** (the default) — return the k nearest vectors.
  - Use `similarity_search_with_score` so you get the **score** — it lets you set a
    confidence threshold ("if best score < X, the answer probably isn't in the corpus
    — say so instead of guessing").
  - Tuning `k` is a recall/precision trade-off: too small → miss the answer; too big →
    dilute relevance, more cost/latency.
  - *Failure mode:* with redundant chunks, all top-k can be near-duplicates — wasted
    context budget, no new information.

**2. MMR (Maximal Marginal Relevance)** — picks results that are relevant **AND**
  mutually diverse (penalizes a candidate for being too similar to ones already
  chosen). `fetch_k` = candidates considered before diversifying.
  - *Use when:* the corpus has redundancy and you'd otherwise retrieve 3 copies of the
    same fact instead of 3 different aspects of the answer.

**3. Hybrid search (BM25 + vector)** — vector search is great at *semantic* similarity
  but weak on **exact tokens** (error codes, IDs, versions — "HTTP 429", "petId=9999").
  BM25 (classic keyword/TF-IDF) nails those. Run both, merge/re-rank (e.g. reciprocal
  rank fusion).
  - *Use when:* technical corpora — API docs, logs, code — where exact identifiers
    matter. Highly relevant to SDET work (logs are full of error codes).

**4. Re-ranking** — two stages: cheaply over-fetch a large candidate set (k=20–50)
  with vector search, then a **cross-encoder** scores each (query, chunk) pair *jointly*
  and keeps the top 3–5.
  - *Why two stages:* cross-encoders are far more accurate (they see query+doc together,
    not as separate vectors) but too slow to run over the whole corpus — so only on the
    shortlist.

**5. Metadata filtering** — tag each chunk at index time (service, doc_type, version,
  env, date). Retrieval = filter by metadata **first**, then similarity search within
  that subset.
  - *Use when:* multi-source/multi-tenant corpora — don't let a "staging" doc answer a
    "production" question.

**6. Agentic retrieval** — retrieval becomes a **tool** the model decides whether to
  call, what query to issue (it can rewrite the user's question), and whether to call
  again with a refined query (`learn/07` Part C; also `learn/06` pattern).
  - *Use when:* query complexity varies — sometimes one retrieval suffices, sometimes
    none is needed, sometimes several. Strongest answer for a 50/50 Agents+RAG interview.

**The "mature pipeline" answer (if asked to design retrieval for production):**
> "Metadata filter first to scope the search, hybrid search (BM25 + vector) for
> first-pass recall, over-fetch ~20–30 candidates, re-rank with a cross-encoder down to
> the top 3–5, feed those to generation. If the groundedness eval shows the answer
> isn't supported, that signals either retrieval missed (tune k/chunking) or the query
> needs agentic rewriting."

**Trade-off table (rapid-fire):**

| Technique | Solves | Cost |
|---|---|---|
| Top-k similarity | Baseline semantic match | Low |
| MMR | Redundant/duplicate chunks | Low |
| Hybrid (BM25+vector) | Exact terms/IDs embeddings miss | Medium (two indexes) |
| Re-ranking | Embedding similarity ≠ true relevance | Medium–high (cross-encoder pass) |
| Metadata filtering | Wrong-source/stale results | Low (needs good metadata) |
| Agentic retrieval | Over/under-retrieving; bad initial queries | Higher latency (extra LLM round-trip) |

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

## 6.5 Handling hallucinations + production challenges

### Hallucinations — defense in depth (prevent → detect → recover)

Opener: *"There's no single fix — it's defense in depth. And most RAG hallucinations
are really **retrieval failures**, so I fix retrieval first."*

**Layer 1 — Prevention:**
- **Grounding via RAG** — give the model the facts so it doesn't reach into memory.
- **Strict prompting** — "Answer ONLY from context; if absent, say 'not in docs'"
  (`learn/05`, `learn/07`).
- **Low temperature** (`temperature=0`) — reduces drift (doesn't eliminate; not fully deterministic).
- **Retrieval quality** — if the right chunk is never retrieved, the model invents.
  Fix upstream: better chunking, hybrid search, re-ranking.

**Layer 2 — Detection:**
- **Groundedness / faithfulness judge (LLM-as-judge)** — `learn/07`'s `Groundedness`
  model verifies every claim is supported, returns `unsupported_claims`; demonstrated
  catching a planted lie. **Headline answer.**
- **Confidence thresholds** — use the retrieval **score**; if best chunk < threshold,
  refuse instead of guessing.
- **Citations** — make the model cite which chunk supports each claim, then verify it exists.

**Layer 3 — Recovery:**
- **Refuse gracefully** — "not enough info" beats a confident wrong answer (a false
  "real bug" is worse than "unsure" for an SDET tool).
- **Retry with better retrieval** — agentic RAG rewrites the query and searches again.
- **Human-in-the-loop** for high-stakes — flag the ungrounded answer, don't auto-trust.

**Agent-specific:** agents can hallucinate *tool calls* (invent a tool/bad args). The
structural defense: the model can only call **bound tools**, and the **arg schema
validates** the call before execution — malformed calls are rejected, not run.

**One-liner:** *"Prevent with grounding and strict prompts, detect with a groundedness
judge and score thresholds, recover by refusing or escalating. Most RAG hallucinations
are retrieval failures, so retrieval is the first thing I fix."*

### Other production challenges (with answers)

| Challenge | Problem | Handling |
|---|---|---|
| **Non-determinism / reproducibility** | Same input → different output | `temperature=0`, **pin model version** (`gpt-4o-2024-08-06`), log all I/O, eval suites |
| **Cost & latency** | LLM calls slow/expensive; loops multiply them | Cache, smaller models for easy steps, trim context, **max-iteration caps** |
| **Prompt injection / security** | Malicious text in a doc/input hijacks the agent | Treat retrieved content as **untrusted data, not instructions**; least-privilege + sandboxed tools; no secrets in prompts; output guardrails |
| **Context window limits** | Too much text overflows the window | Retrieve fewer/better chunks (re-ranking); summarize/trim history; "lost in the middle" → key context at the edges |
| **Evaluation** | Testing a non-deterministic system in CI | LLM-as-judge + golden dataset; evals as a **CI gate** with thresholds; regression baselines |
| **Reliability / error handling** | Timeouts, rate limits, malformed output | Retry w/ backoff; structured-output validation + regenerate (`agent_v2` retry loop); fallbacks |
| **Runaway agent loops** | Agent calls tools forever | **Max-iteration guard** + per-run cost/token budget |
| **Data freshness** | RAG index goes stale | Incremental re-index (hash docs, re-embed only changes); TTL |
| **Observability** | Hard to debug *why* the agent acted | **Tracing** (LangSmith) — log every step, tool call, LLM I/O |

**Tie to your code:** non-determinism → temp=0 + pinning · reliability → `agent_v2`
retry loop · runaway loops → max-iteration cap · security → tool execution stays in
your code behind the HITL gate.

---

## 6.6 DeepEval framework — YOUR HEADLINE ASSET

Separate repo: `Combined folder/evals`. A **production** LLM-eval harness. Lead with
THIS for any evaluation / "how do you know your LLM output is good" / "how do you
connect testing with GenAI" question. It bridges all three scored buckets (Python eval
+ TypeScript/Playwright client + CI).

### What it is
LLM evaluation harness built on **DeepEval** (Confident AI). Provides `LLMTestCase`,
an `evaluate()` runner, pytest integration, and metrics incl. RAG-specific ones
(faithfulness, answer relevancy, contextual precision/recall, hallucination). You used
two metric styles: **GEval** and **DAG**.

### GEval vs DAG (the key contrast — they WILL push here)
- **GEval** = LLM-as-judge. Natural-language criteria → CoT + token **logprobs** →
  0–1 score. Flexible, but a single fuzzy judgment.
- **DAG** (`DeepAcyclicGraph`) = a **decision tree** of evaluation:
  `TaskNode` (extract data) → `BinaryJudgementNode` (yes/no) →
  `NonBinaryJudgementNode` (excellent/good/adequate/shallow) → `VerdictNode` (score).
  Example (`report_quality.py`): extract 5 claims → addresses prompt? → claims
  specific & evidence-backed? → rate depth → score.
- **Why DAG for trust:** each decision is **isolated, auditable, and the path to the
  score is traceable** → explainable + reproducible (the exact Adobe-JD language).
- **Honesty nuance (say it):** "Structure, branching, and scoring are deterministic and
  explainable; each node is still an LLM call, so individual judgments aren't perfectly
  deterministic — but isolating each decision makes it far more reliable and auditable
  than one monolithic score, with per-node thresholds." Don't overclaim "fully deterministic."

### Architecture (engineering signals to name)
Config-driven **YAML** (declarative evals) · metric **factory + registry**
(`match/case` dispatch) · multi-format **loaders** (JSON/PDF/Deep Research) ·
provider-agnostic via **LiteLLM** · **FastAPI** REST server · **Docker** · GitHub
Actions **CI** (py3.10–3.12 + TS type-check) · pytest · ruff · pinned deps.

### Playwright × GenAI bridge (your unique edge)
REST API + a **TypeScript client** + a **combined Playwright+evals Docker image** +
**CI sidecar** → your Playwright/TS suite calls the Python evals over HTTP and gates
LLM-content quality in the same pipeline as E2E tests. This is the JD's exact intersection.

### The logprobs war story ("hardest problem" answer — rehearse verbatim)
> "DeepEval's GEval requests `logprobs` to calibrate the confidence of its scores.
> Gemini via the OpenAI-compatible endpoint doesn't support logprobs, so every eval hit
> an error and a 6-attempt retry loop — slow and noisy. I read DeepEval's source, found
> `generate_raw_response`, and subclassed `LiteLLMModel` to short-circuit it to
> `(None, 0.0)`, so DeepEval cleanly falls back to text-based scoring." (`src/evals/models.py`)
Signals: logprobs = model confidence, reading library internals, provider-compat debugging.

### Walkthrough script (~2.5 min)
1. **Problem:** can't exact-match non-deterministic LLM output — how do you QA quality
   at scale, in CI, explainably?
2. **Approach:** DeepEval; GEval for flexible judging, DAG for explainable/auditable scoring.
3. **Example:** walk the `report_quality` DAG node by node.
4. **Architecture:** config-driven YAML, metric factory, loaders, LiteLLM.
5. **Productionization + Playwright bridge:** FastAPI server, TS client, CI sidecar, Docker.
6. **War story:** the logprobs wrapper.
7. **Close:** "This is how I make non-deterministic LLM output testable — explainable,
   CI-gated, reproducible quality scoring."

### Files to re-read before the interview
`src/evals/dags/report_quality.py` (the DAG) · `src/evals/models.py` (logprobs wrapper)
· `src/evals/metrics/factory.py` (registry + dispatch).

---

## 6.7 Playwright MCP + AI-augmented testing (tailored for Chandan's round)

Interviewer = **Chandan Ghosh** (PAC India, ~30K LinkedIn followers — an AI-testing
voice). He's hands-on Playwright + AI-forward. The hot topic in his niche is
**Playwright MCP + LLM**. This is the synthesis of all three of your buckets — own it.
Demo: `learn/08_playwright_mcp_agent.py` (LangGraph agent driving a real browser via MCP).

### What Playwright MCP is
Microsoft ships an official MCP server, **`@playwright/mcp`**, that exposes browser
automation as **MCP tools** (`browser_navigate`, `browser_click`, `browser_type`,
`browser_snapshot`, `browser_fill_form`, … ~23 tools). An LLM agent connects as a
client and drives a real browser from natural language.

### The key design point (say this — it's the differentiator)
It drives the browser via the **accessibility tree (a structured snapshot), NOT
screenshots**. So it's **fast, deterministic, and token-cheap** — no vision model
needed, and the model acts on stable element roles/names rather than pixel guesses.

### How it wires together (ties to lesson 6 + the MCP talk-track)
```
LLM (brain)        -> gpt-4o
Orchestration loop -> create_react_agent (agent<->tools loop, lesson 6)
Tools              -> NOT hand-written @tool — pulled from the Playwright MCP SERVER
Bridge             -> langchain-mcp-adapters turns MCP tools into LangChain tools
```
`MultiServerMCPClient({...})` launches `npx @playwright/mcp` over stdio →
`await client.get_tools()` → `create_react_agent(model, tools)`.

### Why it matters for testing (AI-augmented testing)
- **NL test authoring** — describe a flow in English; the agent drives the browser and
  you capture the steps as a test.
- **Self-healing / exploration** — the agent navigates by accessibility roles, so it's
  resilient to brittle selectors; it can explore an app and surface issues.
- **Where it fits vs classic Playwright:** you still keep deterministic, committed
  Playwright specs for regression; the agent is for *authoring, exploration, and
  triage* — not for replacing your stable suite. (Say this — it shows judgment.)

### Your talk-track (the dream-question answer)
> "That's the intersection I've been working in. MCP standardizes the *tools* layer of
> an agent, so Playwright MCP turns the browser into a tool an LLM can drive — via the
> accessibility tree, so it's deterministic and cheap, not screenshot-based. I've built
> the agent side — a LangGraph tool-calling loop — and the Playwright side separately;
> combining them, an agent reads a user story, drives the browser through Playwright
> MCP, and self-authors or self-heals tests. I'd keep my committed Playwright specs for
> regression and use the agent for authoring and triage — and close the loop with my
> DeepEval harness to score whether the generated tests are actually valid."

### Likely follow-ups
- *Screenshots vs accessibility tree?* — "Accessibility tree: structured, deterministic,
  token-cheap, no vision model; screenshots are pixel-based, costly, flakier."
- *Would you let an agent run your whole suite?* — "No — deterministic specs for
  regression; agent for authoring/exploration/triage. Don't pay for agency you don't need."
- *How is this different from just calling Playwright in code?* — "MCP is the *standard
  protocol* so any LLM client gets the tools with no custom glue — N+M, not N×M."

### Run it (in YOUR terminal — a real Chrome window opens)
```bash
export OPENAI_API_KEY=sk-...
python learn/08_playwright_mcp_agent.py
```
Target: Playwright's own demo app `https://demo.playwright.dev/todomvc`. The agent
navigates, adds two todos, and reports the remaining count — a real interactive test
flow it sequences itself. Key flags: `--isolated` (fresh profile, no lock) and the
model bound with `parallel_tool_calls=False` (one browser session can't take concurrent
calls). Verified: MCP connects, 23 tools load, agent sequences navigate→type→snapshot.
(Pages only render with a real display session — run it in your own terminal, which has
one; a sandboxed/CI wrapper leaves the page on about:blank.)

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
