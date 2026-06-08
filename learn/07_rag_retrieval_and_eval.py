"""
LESSON 7 — RAG, the parts that earn the 33% score: RETRIEVAL QUALITY + EVALUATION.

Lessons 4-5 built the pipeline. This is the depth an interviewer digs into:
  PART A: retrieval strategies (similarity top-k WITH SCORES, vs MMR for diversity)
  PART B: EVALUATION — "how do you know your RAG is any good?" (LLM-as-judge for
          groundedness/faithfulness — the single most important RAG metric)
  PART C: AGENTIC RAG — making retrieval a TOOL the agent calls (ties to lesson 6)

Run:
    python learn/07_rag_retrieval_and_eval.py
"""

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, Field

KB = [
    "The /pets endpoint accepts a `limit` query param. Max is 100; above 100 -> HTTP 400 LIMIT_TOO_LARGE.",
    "POST /pets requires name and species. Allowed species: dog, cat, bird. Missing fields -> HTTP 422.",
    "Auth uses a Bearer token. Missing/expired token -> HTTP 401 AUTH_REQUIRED.",
    "Rate limit is 100 requests/minute per client. Exceeding it -> HTTP 429 THROTTLED.",
    "Pagination uses an opaque `cursor` param returned in the `next` field of each response.",
]

store = InMemoryVectorStore(OpenAIEmbeddings(model="text-embedding-3-small"))
store.add_texts(KB)
llm = init_chat_model("openai:gpt-4o", temperature=0)

question = "What limit can I pass to /pets and what happens if I go over it?"

# ===================== PART A: RETRIEVAL STRATEGIES =====================
print("=== PART A: retrieval ===")

# (1) Similarity WITH SCORES. The score tells you how confident the match is —
#     crucial for setting a threshold ("if best score < X, say 'I don't know'").
#     Tuning k is a recall/precision trade-off: too small -> you miss the answer;
#     too big -> you stuff irrelevant chunks and the model gets distracted.
scored = store.similarity_search_with_score(question, k=3)
for doc, score in scored:
    print(f"  score={score:.3f}  {doc.page_content[:70]}")

# (2) MMR (Maximal Marginal Relevance): picks results that are relevant AND
#     diverse, so you don't get 3 near-duplicate chunks. Use it when your corpus
#     has lots of redundancy. fetch_k = how many to consider before diversifying.
print("\n  -- MMR (relevance + diversity) --")
mmr = store.max_marginal_relevance_search(question, k=3, fetch_k=5)
for doc in mmr:
    print(f"  mmr   {doc.page_content[:70]}")

# Other strategies to NAME in the interview (not all demoed here):
#   - Hybrid search: combine BM25 keyword search + vector search, then merge.
#     Catches exact terms (error codes, IDs) that embeddings sometimes miss.
#   - Re-ranking: over-fetch (k=20), then a cross-encoder re-scores the top hits.
#   - Metadata filtering: restrict retrieval by tags (e.g. service=auth, env=prod).

context = "\n".join(d.page_content for d, _ in scored)

# ===================== generate the answer =====================
answer = llm.invoke([
    SystemMessage(content="Answer ONLY from the context. If absent, say 'not in docs'."),
    HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"),
]).content
print(f"\n=== ANSWER ===\n{answer}")


# ===================== PART B: EVALUATION (LLM-as-judge) =====================
# "How do you know it's correct?" -> you SCORE it. The top RAG metric is
# GROUNDEDNESS / FAITHFULNESS: is every claim in the answer supported by the
# retrieved context? (Catches hallucination.) Other metrics worth naming:
# answer-relevance, context-precision/recall; tools: RAGAS, LangSmith evals.
print("\n=== PART B: groundedness eval (LLM-as-judge) ===")

class Groundedness(BaseModel):
    grounded: bool = Field(description="True only if EVERY claim is supported by the context")
    unsupported_claims: list[str] = Field(description="Claims not backed by the context")

judge = llm.with_structured_output(Groundedness)

def grade(ans: str) -> Groundedness:
    return judge.invoke([
        SystemMessage(content="You are a strict RAG grader. Is the ANSWER fully supported by the CONTEXT?"),
        HumanMessage(content=f"CONTEXT:\n{context}\n\nANSWER:\n{ans}"),
    ])

good = grade(answer)
print(f"  real answer    -> grounded={good.grounded}  unsupported={good.unsupported_claims}")

# Prove the judge actually discriminates: feed it a planted hallucination.
planted = "You can pass a limit up to 500, and going over returns HTTP 200 with a warning."
bad = grade(planted)
print(f"  planted lie    -> grounded={bad.grounded}  unsupported={bad.unsupported_claims}")
print("  -> a groundedness judge is how you catch hallucinations automatically.")


# ===================== PART C: AGENTIC RAG =====================
# Plain RAG always retrieves. AGENTIC RAG makes retrieval a TOOL the agent may or
# may not call (and can call repeatedly, refining the query). Same loop as lesson 6.
print("\n=== PART C: agentic RAG (retrieval as a tool) ===")

@tool
def search_api_docs(query: str) -> str:
    """Search the API knowledge base for the most relevant doc snippets."""
    hits = store.similarity_search(query, k=2)
    return "\n".join(h.page_content for h in hits)

agent_llm = init_chat_model("openai:gpt-4o", temperature=0).bind_tools([search_api_docs])
msgs = [
    SystemMessage(content="Use search_api_docs to ground every answer. Don't guess."),
    HumanMessage(content="If I send 200 requests in a minute, what error do I get?"),
]
step1 = agent_llm.invoke(msgs)              # model decides to call the tool
if step1.tool_calls:
    call = step1.tool_calls[0]
    print(f"  agent chose to retrieve: search_api_docs({call['args']})")
    from langchain_core.messages import ToolMessage
    result = search_api_docs.invoke(call["args"])
    msgs += [step1, ToolMessage(content=result, tool_call_id=call["id"])]
    final = agent_llm.invoke(msgs)          # model answers using what it retrieved
    print(f"  agentic answer: {final.content}")
print("\n  -> retrieval became a decision, not a fixed first step. That's agentic RAG.")
