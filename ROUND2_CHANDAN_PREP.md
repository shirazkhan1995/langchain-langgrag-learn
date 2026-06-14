# Round 2 Prep — Chandan Ghosh (Panasonic Avionics)

Companion to [INTERVIEW_PREP.md](INTERVIEW_PREP.md). That doc is the **content bank**
(LangGraph, RAG, agents, eval — all still valid). **This** doc is the **strategy + schedule +
gap-fills** tuned to *this specific interviewer*, who is very different from a generic round.

- **Interview:** Wednesday **2026-06-17**. Today is Sunday 2026-06-14 → **3 prep days** (Sun/Mon/Tue) + Wed morning.
- **Round:** 2nd round (you cleared intervue.io round 1). Likely a deeper, human, hands-on technical + culture-fit round.
- **Role:** GenAI SDET II.

---

## 1. Who Chandan is (and why it changes everything)

**Verified from his profile + posts:**
- **Current:** **QA Lead** at **Panasonic Avionics Corporation (PAC)**, India (Bengaluru/Noida). ~30K LinkedIn followers — a genuine **AI-testing content creator/influencer**.
- **Trajectory (~13 yrs):** senior automation @ **Allscripts** (US Healthcare / EHR — high-stakes, compliance-heavy) → **Associate Technical Lead @ TO THE NEW** (US Healthcare + E-commerce clients) → **QA Lead @ Panasonic Avionics**.
- **His own headline:** *QA Lead | Python Automation | Playwright | PyTest | Selenium | API Testing | AI/ML & GenAI Testing | Agentic AI | RAG | MCP | Amazon Strands Agents | LLM Evaluation | Cloud, Microservices & Distributed Systems Testing.*
- **Old stack (Allscripts):** Selenium WebDriver, Python, Workato, Docker Swarm, **Jenkins**.

**What his two posts tell us (decisive):**

**Post A — the OOP warning shot.** He interviews candidates and is openly critical that they "emphasize Python skills" but lack **fundamental OOP concepts, terminology, and exception handling** — "proficient in lists and tuples but challenged by advanced topics." His advice: *master Python comprehensively, core concepts + practical implementation.*
→ **He will probe Python fundamentals. Surface-level Python gets you marked down. This is your #1 gap (it's not in INTERVIEW_PREP.md at all).**

**Post B — the centerpiece overlap.** He built an **AI-powered MCP tool for API automation (FastMCP + RAG + embeddings)** that:
- reads Swagger/OpenAPI to understand the APIs,
- **RAGs over your *existing* test framework** (assertion patterns, reusable flows, utilities),
- generates new tests that **match house style** ("look like your team actually wrote them").
- His scorn: *"Most AI test generators fail because they ignore existing frameworks and produce generic, unusable scripts."*
- His vision: *self-improving QA systems; "the future SDET won't just write test cases — they'll build systems that understand code, learn from past tests, and generate better ones."*

→ **Your `agent.py` is an OpenAPI→pytest generator — exactly the "naive" version he criticizes.** This is the highest-leverage moment of the interview. Framed wrong, it looks like the thing he dismisses. Framed right (§3), it's a peer-level conversation where you independently arrive at his exact insight and show you have the components to build it.

### The re-orientation (vs round 1)

INTERVIEW_PREP.md was built for round-1's even split (Agents 33 / RAG 33 / Playwright 34). For Chandan, **re-weight hard**:

| Priority | Topic | Why | Where it lives |
|---|---|---|---|
| **P0** | **Python fundamentals & OOP** | His explicit interview filter (Post A) | §4 (NEW — gap fill) |
| **P0** | **AI test-gen ↔ his MCP tool** | The centerpiece overlap (Post B) | §3 |
| **P1** | **API testing + PyTest depth** | Headline + his recent build | §5 |
| **P1** | **RAG / MCP / Agentic / LLM-eval** | His headline = your home turf | INTERVIEW_PREP §6, §6.6, §6.7 |
| **P1** | **Playwright framework depth** | Headline; he's Python-Playwright | §6 (NEW — gap fill) |
| **P2** | **Selenium + PW-vs-Selenium** | His roots; likely contrast Q | §6 |
| **P2** | **Cloud/microservices/distributed testing** | In his headline | §7 |
| **P2** | **Behavioral / builder rapport** | He's a creator; mirror his values | §8 |

**Two postures to hold all interview:**
1. **Fundamentals-first.** Mirror Post A. Never hide behind a buzzword; always be able to explain the layer beneath it ("MCP is just a standard protocol for exposing tools — here's what's actually on the wire").
2. **Framework-agnostic.** He names Strands + FastMCP, you used LangGraph. Say: *"I built it in LangGraph, but the primitives — tool-calling loop, MCP tool layer, structured output, checkpointing — transfer directly to Strands or FastMCP. The concept is the asset, not the library."*

---

## 2. The 3-day schedule (Sun → Wed)

Ratio for these days: ~**30% hands-on** (re-run, tweak, open a trace) / **70% explaining out loud**. Your credibility is "I built it"; your *score* is what you can articulate.

### SUNDAY (today, remaining hours) — Reframe + Python fundamentals
1. **Read this doc fully.** Internalize the re-weighting and the two postures.
2. **Python OOP & fundamentals (§4) — the big one.** Work through every item; *say each definition out loud* and write a 5-line example. Target: you can define encapsulation/abstraction/inheritance/polymorphism crisply, explain `try/except/else/finally`, write a custom exception, and explain decorators/generators/context managers.
3. **Study the centerpiece (§3).** Re-read Chandan's Post B. Re-skim your `agent.py`/`agent_v2.py`. Rehearse the flip talk-track until it's natural.

### MONDAY — Playwright depth + API/PyTest
1. **Playwright framework engineering (§6).** Architecture (why it's stable/fast vs Selenium), auto-waiting & web-first assertions, locator strategy, fixtures, POM, config/projects, parallelism & sharding, **trace viewer**, network mocking, `storageState` auth. **Run your `Combined folder/playwright_e2e_test` suite and open one trace** so you can describe it from memory.
2. **API testing + PyTest (§5).** Fixtures/`conftest.py`/`parametrize`/markers, `requests`/`httpx`, assertion design, schema validation, request chaining, `pytest-xdist` parallelism. Connect to `agent.py`'s generated pytest output.
3. **Selenium contrast (§6).** WebDriver/JSON-wire, wait types & why flakiness, the PW-vs-Selenium table.

### TUESDAY — AI×testing synthesis + full mock
1. **Synthesis pass at his intersection:** Playwright MCP agent (`learn/08`) · agentic RAG (`learn/07`) · LLM eval (DeepEval GEval/DAG/groundedness, INTERVIEW_PREP §6.6) · self-healing & AI test-gen. Be able to draw the whole picture on a whiteboard: *user story → agent drives browser via Playwright MCP → generates/heals tests → DeepEval scores validity → CI gate.*
2. **Full out-loud mock (§9 question bank):** 60–90 min. Record yourself. Cover: intro, project walkthrough, the centerpiece, Python fundamentals rapid-fire, Playwright deep-dive, "where does AI break / when NOT to use it."
3. **Prepare your questions for him (§8).** Lock 4–5.

### WEDNESDAY morning — Warm-up only (no new material)
- Re-skim §3 (centerpiece), §4 cheat-sheet, §9 one-liners.
- Run ONE lesson to stay loose (e.g. `learn/01` or `learn/06`).
- Logistics: link/room, water, your code open in tabs, quiet space, charged. Breathe.

---

## 3. ⭐ The centerpiece: his MCP API-test-gen tool ↔ your project

This is the moment that wins or loses the round. **Expect him to steer here** — it's his favorite topic and your project sits right on it.

**The trap:** if you present `agent.py` as "I generate pytest from an OpenAPI spec," that *is* the generic Swagger→test generator he publicly dismisses. Don't stop there.

**The flip (rehearse verbatim until natural):**
> "I built an OpenAPI→pytest workflow — parse the spec, generate tests, run them, and an LLM triages the failures. But the obvious limitation is exactly the one you wrote about: a spec-only generator produces *generic* tests that don't match an existing framework's conventions — its fixtures, assertion helpers, naming, reusable flows. The fix is **RAG over the existing test suite**: embed the current tests, retrieve the assertion patterns and utilities at generation time, and condition the model on them so the output looks like the team wrote it. I've actually built every piece that needs — the RAG pipeline, an MCP integration, and a DeepEval harness to score whether generated tests are *valid* and grounded — I just haven't wired them into that specific 'learn-from-your-own-framework' loop yet. That's the natural next iteration."

**Why this lands with him specifically:**
- You **independently identify his exact insight** (don't ignore the existing framework) — peer-level, not parroting.
- You show **judgment about the limitation of your own work** (he values precision/honesty — Allscripts healthcare background).
- You **already own the components** (RAG, MCP, eval) — you're not theorizing.
- It naturally pivots into your strongest material: RAG retrieval strategies, MCP, and **LLM evaluation** (his headline skill).

**Be ready for his follow-ups:**
- *"How would you RAG over a test suite?"* → "Structure-aware chunking — each test function / fixture / helper is a unit, with metadata (module, tags, the endpoint it covers). Retrieve by the target endpoint + semantic similarity to pull the relevant assertion patterns and utilities. It's the document-structure-aware strategy from my chunking work, applied to code." (INTERVIEW_PREP §6 chunking)
- *"How do you know the generated test is any good?"* → pivot to **DeepEval**: "I score it. Does it parse and collect under pytest (deterministic gate)? Then an LLM-as-judge / DAG checks it actually asserts on the spec'd behavior and reuses house utilities. That's my eval harness — GEval for flexible judgment, DAG for an auditable, node-by-node score." (INTERVIEW_PREP §6.6)
- *"What about self-improving — learning from failures?"* → "That's the agentic loop: a failed test's triage output becomes feedback; the agent regenerates with that context. My `agent_v2` already does a bounded self-healing retry on generation failures — extending it to learn from *runtime* failures is the same pattern with a longer memory (RAG over past failures)."
- *"FastMCP vs what you used?"* → "I used LangChain's MCP adapters to consume an MCP server (Playwright MCP) as tools. FastMCP is for *authoring* a server. Same protocol, opposite ends of the wire — and that's the point of MCP: the client and server are decoupled by a standard."

---

## 4. 🐍 Python fundamentals & OOP — P0 GAP FILL (his explicit filter)

He fails candidates here. Be able to **define each term in one clean sentence AND show a tiny example**. Tie OOP back to **test framework design** — that's *why* a QA lead cares (Page Object Model = classes + inheritance; fixtures = composition).

### The 4 pillars of OOP (know cold)
- **Encapsulation** — bundle data + the methods that operate on it inside an object, and control access. Python convention: `_protected`, `__private` (name-mangled to `_Class__x`), expose via `@property`. *"A Page Object encapsulates a page's locators and actions; tests touch the methods, not the selectors."*
- **Abstraction** — expose *what* an object does, hide *how*. `abc.ABC` + `@abstractmethod` defines a contract subclasses must implement. *"A `BasePage` abstract class forces every page to implement `is_loaded()`."*
- **Inheritance** — a subclass reuses/extends a base class (`class LoginPage(BasePage)`), calls up with `super().__init__()`. Python supports **multiple inheritance**, resolved by **MRO** (C3 linearization; inspect with `Class.__mro__`).
- **Polymorphism** — one interface, many implementations. Python is **duck-typed**: "if it has `.click()`, I can call `.click()`" — no shared base needed. Includes **method overriding**. (Python has **no method overloading**; use default/`*args` or `functools.singledispatch`.)

### Terminology he'll expect you to nail
- **class vs instance(object)**: class = blueprint; instance = a built object. `type(obj)` / `isinstance(obj, Cls)`.
- **instance vs class vs static methods**:
  - instance method `def m(self)` — operates on the instance.
  - `@classmethod def m(cls)` — operates on the class (great for **alternative constructors**: `Page.from_url(...)`).
  - `@staticmethod def m()` — namespaced utility, no `self`/`cls`.
- **instance vs class variables**: class vars are shared across instances (watch the **mutable class-attribute** trap). Instance vars live on `self`.
- **`@property`** — method that reads like an attribute; gives a getter/`@x.setter` without breaking the API. The Pythonic alternative to Java getters/setters.
- **dunder / magic methods** — `__init__` (constructor), `__repr__` vs `__str__` (debug vs user string), `__eq__`/`__hash__`, `__len__`, `__enter__`/`__exit__` (context manager), `__call__`, `__iter__`/`__next__`.
- **composition vs inheritance** — "has-a" vs "is-a". *"Prefer composition for test utilities — a `LoginPage` *has* an `APIClient`, it isn't one. Favor composition over deep inheritance trees."* (A mature, framework-design answer he'll respect.)

### Exception handling (he calls this out by name)
```python
try:
    resp = client.get(url)
    resp.raise_for_status()
except TimeoutError as e:
    raise FlakyTestError("network timeout") from e   # chaining: preserves cause
except HTTPError:
    ...                       # handle 4xx/5xx
else:
    return resp.json()        # runs only if NO exception
finally:
    client.close()            # ALWAYS runs (cleanup) — even on return/raise
```
- `else` = "ran without error"; `finally` = "always, for cleanup."
- **Custom exceptions**: `class FlakyTestError(Exception): ...` — domain-specific, catchable by type.
- **`raise ... from e`** = exception chaining; preserves the root cause in the traceback.
- **EAFP vs LBYL** — Python prefers **EAFP** ("easier to ask forgiveness": try/except) over **LBYL** ("look before you leap": if-checks). Know the term — it's a fundamentals tell.
- Catch **specific** exceptions, never bare `except:`. `except Exception` at boundaries only, and re-raise or log.

### "Advanced topics" freshers miss (he said so) — be ready
- **Decorators** — a function that wraps another to add behavior (`@retry`, `@pytest.fixture`, `@property`). Be able to write a simple one with `functools.wraps`. *"`@pytest.fixture` and `@pytest.mark.parametrize` are decorators — I use them every day."*
- **Generators / iterators** — `yield` produces values lazily (memory-efficient for large data/streams). `iter()`/`next()`, the iterator protocol.
- **Context managers** — `with` + `__enter__`/`__exit__` (or `@contextmanager`) for guaranteed setup/teardown (files, browsers, DB sessions). *"Playwright's `with sync_playwright() as p:` is a context manager — guaranteed cleanup."*
- **`*args` / `**kwargs`** — variadic positional/keyword args; `*`/`**` for unpacking.
- **Mutable default argument trap** — `def f(x, acc=[])` shares one list across calls; use `acc=None` then `acc = acc or []`. Classic gotcha question.
- **`is` vs `==`** — identity vs equality. **shallow vs deep copy** (`copy` vs `copy.deepcopy`).
- **list vs tuple vs set vs dict** — he noted candidates *only* know these, so know them PLUS *when* each (tuple = immutable/hashable → dict key; set = membership/dedup O(1)).
- **GIL (one-liner)** — "CPython's Global Interpreter Lock serializes bytecode, so threads don't give true CPU parallelism — fine for **I/O-bound** test work (network waits), use **multiprocessing** for CPU-bound. Playwright/pytest-xdist parallelize across **processes/workers**, sidestepping the GIL."

> **Connect it back every time:** OOP isn't trivia to him — it's *how you architect a test framework*. POM = encapsulation + inheritance; fixtures = composition + dependency injection; custom exceptions = readable failures; decorators = pytest itself. Say that and you've answered the question *and* shown you're a framework engineer.

---

## 5. API testing + PyTest depth — P1 (his headline + recent build)

### PyTest (your generated tests are pytest — own this)
- **Fixtures** — setup/teardown via dependency injection; `@pytest.fixture(scope="session|module|class|function")`; `yield` for teardown; `conftest.py` shares fixtures across files without imports.
- **Parametrize** — `@pytest.mark.parametrize("inp,exp", [...])` runs one test over many cases (data-driven). Mention **boundary/equivalence** thinking when choosing cases.
- **Markers** — `@pytest.mark.smoke`, `-m "smoke and not slow"`; `skip`/`xfail`.
- **Assertions** — pytest rewrites `assert` for rich introspection (no `assertEquals` needed).
- **Parallelism** — `pytest-xdist` (`-n auto`) runs across worker processes (GIL-safe); needs test isolation.
- **Reporting/plugins** — `pytest-html`, `--junitxml` for CI, `pytest-cov`.

### API testing fundamentals
- **Layers**: status code → headers → **schema/contract** (validate body shape, e.g. `jsonschema`/Pydantic) → business assertions → side effects.
- **`requests`/`httpx`** (httpx adds async + HTTP/2). Sessions for connection reuse + auth.
- **Request chaining / state**: create → read → update → delete, threading IDs through (your petstore `petId`); fixtures to set up/tear down test data.
- **Positive + negative + edge**: 2xx happy path, 4xx (bad input, auth), 5xx, rate-limits, idempotency, pagination.
- **Playwright's `APIRequestContext`** — Playwright does API testing too (`request.get/post`), and lets you mix API setup with UI tests (seed via API, assert via UI). Good to name — unifies his two headline areas.
- **Contract testing** (→ §7) — for microservices, Pact-style consumer/provider contracts so services can deploy independently.

---

## 6. Playwright framework depth + Selenium — P1/P2 GAP FILL

INTERVIEW_PREP §6.7 covers Playwright **MCP** (the AI angle). This section is **classic Playwright engineering**, which a Playwright/PyTest lead *will* probe and isn't in your other doc.

### Why Playwright is fast & stable (architecture — the headline)
- One persistent **WebSocket/CDP** connection to the browser (vs Selenium's per-command HTTP round-trips over the **W3C WebDriver/JSON-wire** protocol). Fewer round-trips → faster, less flaky.
- **Auto-waiting**: every action (`click`, `fill`) auto-waits for the element to be **actionable** (attached, visible, stable, enabled). Kills most explicit-wait flakiness.
- **Web-first assertions**: `expect(locator).toBeVisible()` **auto-retries** until timeout — no manual sleeps.
- **Browser contexts**: lightweight isolated sessions (own cookies/storage) — cheap parallelism + clean isolation per test.

### Locators (resilience — ties to his "self-healing" interest)
- Prefer **user-facing** locators: `get_by_role`, `get_by_label`, `get_by_text`, `get_by_test_id` — resilient to DOM churn vs brittle XPath/CSS. Locators are **lazy** (resolved at action time, so they re-query — naturally resistant to staleness).
- *"Good locator strategy is the low-tech 'self-healing' — pick semantic, user-facing locators and most DOM changes don't break you. AI self-healing is the layer on top for the rest."*

### Framework building blocks
- **Fixtures** (pytest-playwright gives `page`, `context`, `browser`; write custom ones for auth/data) — DI + scoping (worker vs test).
- **Page Object Model** — encapsulate page locators+actions in classes (→ your OOP answer in §4).
- **Config / projects** — multi-browser (chromium/firefox/webkit) & device projects, `retries`, `trace`, `reporter`, `baseURL`.
- **`storageState`** — log in once, save auth state, reuse across tests (skip per-test login).
- **Network interception** — `route`/`fulfill` to mock/stub APIs, force error states, speed up tests.
- **Parallelism & sharding** — parallel by default across workers; **`--shard=1/3`** splits a suite across CI machines.
- **Trace Viewer** — `trace: on`; records DOM snapshots, network, console per step → time-travel debugging. **Run your suite and open one trace before Monday** so you can describe it firsthand. Also: video, screenshots, `--ui` mode.

### Selenium contrast (he came up through it)

| | **Playwright** | **Selenium** |
|---|---|---|
| Protocol | WebSocket/CDP, persistent | W3C WebDriver, per-command HTTP |
| Waiting | Auto-wait + retrying assertions | Manual waits (implicit/explicit/fluent) → flaky if misused |
| Speed/flakiness | Faster, more stable | Slower, flakier without discipline |
| Setup | One install, browsers bundled | Driver/browser version management |
| Maturity/ecosystem | Newer, momentum | Huge legacy ecosystem, Grid |
| Languages | TS/JS, **Python**, Java, .NET | Many |

- **Selenium waits**: *implicit* (global poll), *explicit* (`WebDriverWait` + `expected_conditions`), *fluent* (custom poll/ignore). Flakiness usually = mixing implicit+explicit or fixed `sleep()`.
- Balanced take: *"Selenium is battle-tested with a massive ecosystem and Grid; Playwright's architecture removes most flakiness by default. For greenfield I'd pick Playwright, but I respect that Selenium runs an enormous amount of the world's regression suites."* (Don't trash Selenium — it's his roots.)

---

## 7. Cloud / microservices / distributed-systems testing — P2 (his headline)

Be conversational, not expert:
- **Test pyramid for microservices**: lots of unit + **contract tests**, fewer integration, fewest E2E (E2E across many services is slow/flaky → keep thin).
- **Contract testing (Pact)** — consumer/provider contracts let services deploy independently without full E2E every time. Name this; it's the key microservices-testing concept.
- **Distributed challenges**: eventual consistency, async/event-driven flows (test by polling/awaiting events, not fixed sleeps), idempotency, partial failures, retries/timeouts, observability-driven testing (assert on traces/logs).
- **Containers/CI**: he used **Docker Swarm + Jenkins**; you used Docker + GitHub Actions. *"Concepts transfer — containerized test envs, parallel pipeline stages, gating."*

---

## 8. Behavioral, rapport & questions to ask him

He's a **builder and a creator** — treat it as a peer technical conversation, not an exam.

**Mirror his values:**
- **Fundamentals over hype** (his Post A): when you mention something shiny, immediately show the layer beneath.
- **Honesty about limits** (healthcare background): say "I haven't built X yet, but here's how I would and here are the pieces I have." Beats overclaiming. A false "it works" is worse than "here's the boundary."
- **Builder energy** (his Post B): "I built…", "the bug I hit was…", "the next iteration is…". Your war stories (INTERVIEW_PREP §6.7) are perfect.

**Questions to ask him (lock 4–5 — these flatter his actual work and start a real conversation):**
1. "Your MCP tool that RAGs over the existing test suite to match house style — how did you handle keeping generated tests *grounded* in the real framework vs the model drifting? Did you put an eval gate on the output?" *(shows you read/understood his work AND surfaces your eval strength.)*
2. "Where have you found AI-augmented testing genuinely pays off vs where it's still hype — authoring, triage, maintenance, self-healing?"
3. "You list **Amazon Strands** alongside MCP/RAG — how are you choosing between agent frameworks for testing workloads? What made Strands fit?"
4. "How does the team at Panasonic Avionics balance AI-generated tests against a deterministic regression suite for safety-relevant systems?" *(nods to avionics rigor.)*
5. "For an SDET II joining now, what separates someone who *uses* AI tools from someone who *builds* the testing systems you described?"

**Likely behavioral beats:** why this role / why GenAI SDET, a hard bug you debugged (→ the **stateful-MCP infinite-loop** story or the **logprobs** wrapper), how you keep a non-deterministic system testable (→ DeepEval), a time you chose *not* to use the fancy approach (→ "workflow over agent; don't pay for agency you don't need").

---

## 9. Tailored question bank (rehearse out loud)

**P0 — Python fundamentals (he WILL ask; see §4)**
- [ ] Define the 4 OOP pillars, one sentence + example each.
- [ ] instance vs class vs static method — when each? `@classmethod` as alt constructor.
- [ ] `try/except/else/finally` semantics; write a custom exception; `raise from`; EAFP vs LBYL.
- [ ] Decorator: what & write a simple `@retry`. Generator: what & when. Context manager: what & `__enter__/__exit__`.
- [ ] Mutable-default-arg trap; `is` vs `==`; shallow vs deep copy; GIL one-liner.
- [ ] "How does OOP show up in your test framework?" → POM/fixtures/exceptions/decorators.

**P0 — The centerpiece (§3)**
- [ ] The flip: OpenAPI→pytest is the naive version; RAG-over-existing-tests is the real win; I own the pieces.
- [ ] How would you RAG over a test suite? (structure-aware chunking by test/fixture/helper + metadata)
- [ ] How do you know the generated test is good? (DeepEval: deterministic gate + LLM-judge/DAG)

**P1 — API / PyTest (§5)**
- [ ] Fixtures, scopes, conftest, parametrize, markers, xdist parallelism.
- [ ] What do you assert on an API response? (status→schema→business→side effects; +/- /edge)
- [ ] Playwright APIRequestContext; contract testing for microservices.

**P1 — RAG / Agents / MCP / Eval (INTERVIEW_PREP §6, §6.6, §6.7)**
- [ ] Workflow vs agent; the 5 LangGraph primitives; ReAct loop; when NOT to use an agent.
- [ ] Chunking strategies & the precision/context tension; retrieval (top-k/MMR/hybrid/re-rank/metadata/agentic).
- [ ] **LLM Evaluation** (his headline): GEval vs DAG; groundedness/faithfulness; eval as a CI gate. Lead with DeepEval.
- [ ] MCP: what's on the wire; stateful vs stateless (the Playwright-MCP war story); FastMCP (author) vs adapters (consume).
- [ ] Framework-agnostic: LangGraph concepts → Strands/FastMCP.

**P1/P2 — Playwright / Selenium (§6)**
- [ ] Why Playwright is fast/stable (architecture, auto-wait, web-first assertions).
- [ ] Locator strategy & resilience; trace viewer (describe from having opened one); sharding; storageState; network mocking.
- [ ] Playwright vs Selenium (the table); Selenium wait types & flakiness causes.

**P2 — Distributed / behavioral (§7, §8)**
- [ ] Microservices test pyramid + contract testing; testing async/eventual-consistency.
- [ ] Hardest bug; non-determinism in CI; a time you chose the simpler design; your 4–5 questions for him.

---

## 10. The 6 things to get right on the day

1. **Lead fundamentals-first**, buzzword-second — always explain the layer beneath. (His Post A.)
2. **Nail the centerpiece flip** (§3) — it's your strongest, most-tailored moment.
3. **Be framework-agnostic** — concepts transfer to Strands/FastMCP; don't over-index on LangGraph.
4. **Lead with LLM Evaluation (DeepEval)** for any "how do you know it's good" question — it's literally in his headline.
5. **Show builder honesty** — "built X, hit bug Y, next is Z; haven't done W yet but here's how." No overclaiming.
6. **Engage him as a peer** — ask about his MCP tool; make it a conversation between two people who build testing systems.

> One-line self-summary to have ready: *"I'm an SDET who builds the testing systems, not just the test cases — I've wired LangGraph agents to Playwright via MCP, built RAG pipelines for test/log triage, and a DeepEval harness that makes non-deterministic LLM output CI-gateable. The next thing I want to build is exactly what you posted about: RAG over an existing suite so generated tests match the team's own framework."*
