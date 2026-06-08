"""
LESSON 5 — RAG that's actually useful for an SDET: querying LOGS.

Lesson 4 retrieved from 3 short strings. Real docs/logs are long, so you must
CHUNK them first. This lesson shows the full, real pipeline + the design
choices an interviewer will ask you to whiteboard.

Run:
    python learn/05_rag_over_logs.py

Pipeline:
    1. CHUNK    : split a long log into overlapping windows (RecursiveCharacterTextSplitter)
    2. EMBED    : turn each chunk into a vector (OpenAIEmbeddings)
    3. STORE    : put vectors in a vector store (InMemory here; FAISS/Chroma/pgvector in prod)
    4. RETRIEVE : embed the question, fetch top-k nearest chunks
    5. GENERATE : answer grounded ONLY in those chunks

WHITEBOARD TALK-TRACK (memorize the trade-offs in the comments below).
"""

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# A chunk of a noisy service log (pretend it's thousands of lines).
LOG = """
2026-06-06 09:01:12 INFO  api.gateway  GET /pets?limit=10 200 14ms
2026-06-06 09:01:13 INFO  api.gateway  POST /pets 201 22ms
2026-06-06 09:02:01 WARN  api.auth     token nearing expiry for user 8841
2026-06-06 09:02:44 ERROR api.gateway  GET /pets/9999 404 NOT_FOUND petId=9999
2026-06-06 09:03:10 ERROR db.pool      connection acquire timeout after 5000ms (pool exhausted, size=10, in_use=10)
2026-06-06 09:03:11 ERROR api.gateway  GET /pets 500 INTERNAL upstream=db.pool reason=timeout
2026-06-06 09:03:12 ERROR api.gateway  POST /pets 500 INTERNAL upstream=db.pool reason=timeout
2026-06-06 09:05:00 INFO  api.gateway  GET /pets?limit=10 200 12ms
2026-06-06 09:06:30 WARN  api.ratelimit client 5.5.5.5 throttled: 120 req/min exceeds 100
""".strip()

# 1) CHUNK -------------------------------------------------------------------
# chunk_size = max chars per chunk. chunk_overlap = chars repeated between
# neighbours so a fact split across a boundary isn't lost.
# TRADE-OFF: small chunks => precise retrieval but lose surrounding context;
# big chunks => more context but you pay more tokens and dilute relevance.
# Typical starting point: 500-1000 chars, ~10-20% overlap. Tune by eval.
splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=40)
chunks = splitter.split_text(LOG)
print(f"[chunk] split log into {len(chunks)} chunks")

# 2+3) EMBED + STORE ---------------------------------------------------------
# Embedding model choice: text-embedding-3-small is cheap/fast and fine for most
# retrieval; -3-large is more accurate for nuanced semantic search.
# Vector store choice:
#   InMemoryVectorStore -> demos/tests (what we use here)
#   FAISS / Chroma      -> local, single-machine, free
#   pgvector / Pinecone / Weaviate -> production, persistent, scalable, filtered search
store = InMemoryVectorStore(OpenAIEmbeddings(model="text-embedding-3-small"))
store.add_texts(chunks)

# 4) RETRIEVE ----------------------------------------------------------------
question = "Why did GET /pets start returning 500 errors around 09:03?"
hits = store.similarity_search(question, k=3)   # top-3 most relevant chunks
context = "\n".join(h.page_content for h in hits)
print(f"\n[retrieve] top-{len(hits)} chunks for the question:\n{context}")

# 5) GENERATE ----------------------------------------------------------------
llm = init_chat_model("openai:gpt-4o", temperature=0)
answer = llm.invoke([
    SystemMessage(content=(
        "You are an SRE assistant. Using ONLY the log excerpts provided, explain "
        "the likely root cause. If the logs don't say, reply 'insufficient logs'."
    )),
    HumanMessage(content=f"Log excerpts:\n{context}\n\nQuestion: {question}"),
])
print("\n[generate] grounded root-cause answer:\n", answer.content)

# WHY RAG vs just pasting the whole log into the prompt?
#   - Cost/latency: you only send the relevant slice, not 50k lines.
#   - Accuracy: less irrelevant text => less chance the model gets distracted.
#   - Freshness/scale: re-index new logs without retraining anything.
# WHEN NOT to use RAG: if the doc fits comfortably in context AND you always need
#   all of it, just pass it directly. RAG earns its keep when the corpus is big.
