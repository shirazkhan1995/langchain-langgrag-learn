"""
LESSON 4 — RAG (Retrieval-Augmented Generation) in ~30 lines.

The JD asks for RAG pipelines "to query documentation, logs, and test data."
RAG = before answering, FETCH relevant text and stuff it into the prompt, so the
LLM answers from YOUR docs instead of its memory. Three steps:

    1. INDEX:    chop docs into chunks -> embed each chunk -> store vectors.
    2. RETRIEVE: embed the question -> find the most similar chunks.
    3. GENERATE: put those chunks in the prompt -> LLM answers grounded in them.

Run:
    python learn/04_rag_mini.py

What to notice:
  - "Embeddings" turn text into vectors; similar meaning => nearby vectors.
  - The model answers using the retrieved snippet, and we can SEE which one.
  - Swap `DOCS` for your API docs / log files and you have the JD's RAG bullet.
"""

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

# Pretend these are pages from your internal API docs.
DOCS = [
    "The /pets endpoint supports a `limit` query param. Max allowed limit is 100; "
    "values above 100 return HTTP 400 with error code LIMIT_TOO_LARGE.",
    "Authentication uses a Bearer token in the Authorization header. Missing or "
    "expired tokens return HTTP 401 with code AUTH_REQUIRED.",
    "Creating a pet (POST /pets) requires `name` and `species`. Missing fields "
    "return HTTP 422. Allowed species are: dog, cat, bird.",
]

# 1) INDEX -------------------------------------------------------------------
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
store = InMemoryVectorStore(embeddings)
store.add_texts(DOCS)
print("[index] stored", len(DOCS), "doc chunks as vectors")

# 2) RETRIEVE ----------------------------------------------------------------
question = "What happens if I ask for 500 pets in one request?"
hits = store.similarity_search(question, k=1)   # nearest chunk(s)
context = "\n".join(h.page_content for h in hits)
print("\n[retrieve] best-matching chunk:\n  ", context)

# 3) GENERATE ----------------------------------------------------------------
llm = init_chat_model("openai:gpt-4o", temperature=0)
answer = llm.invoke([
    SystemMessage(content="Answer ONLY from the provided context. If absent, say so."),
    HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"),
])
print("\n[generate] grounded answer:\n  ", answer.content)
print("\nThat's RAG. No fine-tuning — just retrieve-then-prompt.")
