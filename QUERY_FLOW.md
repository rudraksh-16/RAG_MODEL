# Query Flow — Question to Grounded Answer (Detailed Walkthrough)

This document traces the **query pipeline** end to end: every function that runs, in order,
from a user typing a question to a cited answer streaming back to the terminal. It is the
read-side counterpart to `INJECTION_FLOW.md` (the write side). It follows one concrete
question through the whole pipeline.

Entry point: `python -m src.llm.main`

Files involved:

| Step | File | Function |
|---|---|---|
| CLI loop | `src/llm/main.py` | `main` |
| Turn driver | `src/llm/rag/pipeline.py` | `rag_model` |
| Agent | `src/llm/rag/rag_agent/agent.py` | `RagAgent.stream` |
| System prompt | `src/llm/rag/rag_agent/prompt.py` | `SYSTEM_PROMPT` |
| Retrieval tool | `src/llm/rag/rag_agent/tools/make_retrieval.py` | `get_retrieval` → `_run_retrieval` |
| Hybrid search | `src/llm/rag/retrieval/search.py` | `Retriever.hybrid_search` |
| Rerank | `src/llm/rag/retrieval/rerank.py` | `CohereReranker.rerank` |
| Embedder | `src/llm/rag/embeddings/model.py` | `get_embedding_model` |
| Constants | `src/llm/rag/constant.py` | `RAGConstant` |

The chunks being searched were written by the ingestion pipeline — see `INJECTION_FLOW.md`.

---

## 0. The Example

Corpus already ingested (e.g. `leip101.pdf`, including the page 4 "Data Types in MySQL" table
from `INJECTION_FLOW.md`). User runs `python -m src.llm.main` and types:

```
You: What is the VARCHAR data type?
```

We follow this question all the way to the streamed, cited answer.

---

## 1. CLI Loop — `main()`

```python
print("Loading model...")
get_embedding_model()   # load all-mpnet-base-v2 ONCE at startup
get_client()            # open Weaviate connection ONCE at startup
chat_history = []
while True:
    user_input = input("You: ").strip()
    ...
    for token in rag_model(chat_history, user_input):
        print(token, end="", flush=True)   # stream to terminal as it arrives
        parts.append(token)
    answer = "".join(parts)
    if answer:
        chat_history.append({"role": "assistant", "content": answer})
```

- **Warm-up**: the embedder and the Weaviate client are built once at startup so the *first*
  question doesn't pay model-load / connect cost mid-turn (both are module-level singletons).
- `exit` / `quit` (or empty input) are handled before any work.
- The assistant answer is **streamed token-by-token** to stdout and only appended to
  `chat_history` after the full turn — the user turn itself is appended inside the agent
  (see §3). Failed turns yield nothing, so nothing is appended.
- `finally: close_client()` closes Weaviate cleanly on exit.

---

## 2. Turn Driver — `rag_model(chat_history, user_input)`

```python
def rag_model(chat_history, user_input):
    logger.info("RAG TURN START | input=%r", user_input)
    agent = RagAgent()
    try:
        with log_duration(logger, "RAG TURN"):
            yield from agent.stream(chat_history=chat_history, user_message=user_input)
    except Exception as e:
        logger.error("RAG turn failed: %s", e)
```

- A **generator**: builds a fresh `RagAgent`, then delegates straight to `agent.stream(...)`,
  re-yielding each token to the CLI.
- `log_duration` wraps the whole turn → emits the `RAG TURN | N ms` wall-time log line.
- Any exception is caught and logged; the generator simply stops yielding, so the CLI loop
  degrades gracefully (prints a blank answer, stays alive) instead of crashing.

---

## 3. Agent — `RagAgent.stream(chat_history, user_message)`

### 3.1 Construction (`RagAgent.__init__`)

```python
llm = build_llm(provider="openai", model="gpt-4.1-mini", temperature=0.5)
self.agent = create_agent(llm, tools=[get_retrieval], system_prompt=SYSTEM_PROMPT)
self.max_iteration = 5   # RAGConstant.DEFAULT_MAX_ITERATION
```

- LangChain `create_agent` wires the LLM to **one tool** (`get_retrieval`) under the RAG
  system prompt. The LLM itself decides when to call the tool.

### 3.2 Streaming the turn

```python
chat_history.append({"role": "user", "content": user_message})
logger.info("AGENT INVOKED | model=%s | message=%r", ...)

for chunk, _meta in self.agent.stream(
        {"messages": chat_history},
        config={"recursion_limit": self.max_iteration * 2 + 1},   # = 11
        stream_mode="messages"):
    if getattr(chunk, "tool_call_chunks", None):
        used_retrieval = True            # the LLM issued a tool call
    if getattr(chunk, "type", "") == "tool":
        continue                         # skip the raw retrieval payload
    text = chunk.content
    if isinstance(text, str) and text:
        streamed_chars += len(text)
        yield text                       # only the LLM's answer tokens reach the user
```

What happens inside the agent loop (driven by `SYSTEM_PROMPT`, see §4):

1. The LLM reads the question + system prompt and **decides to call `get_retrieval`** with a
   refined, definition-style query (e.g. `"definition of VARCHAR data type in MySQL"`).
2. The tool runs (§5) and returns JSON grounding back into the loop.
3. The LLM reads the grounding and writes the final answer — which is what gets streamed.

Key behaviors:
- `recursion_limit = max_iteration * 2 + 1 = 11` bounds the tool↔LLM ping-pong (the prompt
  allows up to two retrieval attempts before refusing).
- `stream_mode="messages"` yields every message chunk; the code **filters out tool messages**
  (`type == "tool"`) so the user never sees raw retrieved JSON — only the answer.
- `used_retrieval` flag records whether any tool call happened, logged at the end as
  `ANSWER GROUNDED` vs `NO RETRIEVAL` (the latter is a warning — answer came from LLM memory,
  not the DB).

> **Cost note:** the agent spends one LLM round trip to *decide to retrieve*, then another to
> *answer* — that extra hop is the main query latency. See `RAG_FLOW.md` §6.

---

## 4. System Prompt — what governs the agent (`prompt.py`)

`SYSTEM_PROMPT` is strict RAG policy. The parts that shape the flow:

- **Grounding only**: answer ONLY from retrieved documents; prior/general knowledge is
  forbidden.
- **Two-attempt rule**: call `get_retrieval` with a definition-style query. If the answer is
  not explicitly present, *reframe with synonyms and retrieve a second time*. After two failed
  attempts, respond with exactly `"I don't know based on the provided documents."`
- **Citations**: each retrieved doc carries `source_file`, `page_number`, `element_type`. The
  answer must end with `(source: <source_file>, page <page_number>, <element_type>)`, one per
  source used. No citation on the refusal sentence.
- **No leakage**: never mention tools/retrieval/reasoning; exactly one final response per turn.

For our example, the answer about VARCHAR draws on the page 4 table chunk, so the LLM ends
with something like `(source: leip101.pdf, page 4, table)`.

---

## 5. Retrieval Tool — `get_retrieval(query)` → `_run_retrieval(...)`

Called by the LLM (not directly by us). `query` is the LLM's refined wording.

```python
@tool
def get_retrieval(query: str) -> str:
    retriever = Retriever()
    reranker = CohereReranker()
    with log_duration(logger, "RETRIEVAL TOOL"):
        return _run_retrieval(retriever, reranker, query)
```

`_run_retrieval` is **two stages**: broad recall, then precise reranking.

```python
logger.info("WEAVIATE QUERY: %r", query)
docs = retriever.hybrid_search(
    query=query,
    alpha=RAGConstant.HYBRID_SEARCH_ALPHA,     # 0.5
    limit=RAGConstant.RETRIEVAL_CANDIDATES,    # 20
)                                              # → 20 candidate chunks
reranked = reranker.rerank(
    query=query, documents=docs, top_k=RAGConstant.RERANK_TOP_K   # 5
)                                              # → best 5
return json.dumps(reranked)                    # grounding back to the LLM
```

- On any exception: log `RETRIEVAL FAILED` and raise `RuntimeError` (the agent loop sees the
  tool error and can react / the turn fails up to the driver).
- The returned JSON (5 chunks) is what the LLM reads to write the answer.

### 5.1 Hybrid search — `Retriever.hybrid_search(query, alpha, limit)`

```python
vector = self._encode(query)   # all-mpnet-base-v2, normalize_embeddings=True → 768-d
response = self.collection.query.hybrid(
    query=query,               # BM25 keyword side
    vector=vector,             # semantic side
    alpha=alpha,               # 0.5 = equal blend (0 = pure BM25, 1 = pure vector)
    limit=limit,               # 20
    return_properties=SEARCH_PROPERTIES,
)
```

- `_encode` embeds the query the same way chunks were embedded at ingest — 768-d, but here
  with `normalize_embeddings=True`. Logged as `EMBED ENCODE | N ms`.
- Weaviate's `hybrid` runs **BM25 keyword search AND vector search together**, blends the two
  rankings by `alpha=0.5`, and returns the top 20. Logged as `WEAVIATE HYBRID QUERY | N ms`.
- Each result is flattened by `_base_fields()` into a dict carrying `text`, `source`,
  `chunk_index`, and the multimodal metadata (`source_file`, `page_number`, `element_type`,
  `section`, `image_path`) plus the hybrid `score`.
- The tool then logs `WEAVIATE HITS: 20 chunks ... sources=[…]`.

> (`vector_search()` also exists for pure-semantic lookup, but the query path uses
> `hybrid_search`.)

### 5.2 Rerank — `CohereReranker.rerank(query, documents, top_k)`

```python
texts = [doc["text"] for doc in documents]          # the 20 candidate texts
response = self.client.rerank(
    model="rerank-english-v3.0", query=query, documents=texts, top_n=top_k   # 5
)
for r in response.results:
    doc = documents[r.index]
    doc["rerank_score"] = float(r.relevance_score)
    reranked_docs.append(doc)                        # reordered, best first
```

- Cohere's cross-encoder scores each of the 20 candidates against the query *jointly* (more
  accurate than the first-stage hybrid score), keeps the top `5`, and attaches a
  `rerank_score` to each kept doc. Logged as `COHERE RERANK | N ms`.
- `_run_retrieval` then logs `RERANKED top-5 ...` with each kept chunk's source/page/type/score
  — this is exactly the grounding the LLM receives.

---

## 6. Answer

The LLM reads the 5 reranked chunks (JSON), writes the answer **strictly from them**, and
appends the citation line. `RagAgent.stream` yields those answer tokens; `rag_model`
re-yields them; `main` prints each token live. Example:

```
Assistant: VARCHAR(n) is a string data type that stores text up to n characters.
(source: leip101.pdf, page 4, table)
```

If neither retrieval attempt surfaces the answer, the LLM instead emits exactly
`I don't know based on the provided documents.` (no citation).

---

## 7. Full Sequence (one question)

```
main()  [warm-up: get_embedding_model(), get_client()]
│
└─ rag_model(chat_history, "What is the VARCHAR data type?")
   │   RAG TURN START
   └─ RagAgent().stream(...)
      │   AGENT INVOKED
      │   create_agent(gpt-4.1-mini, tools=[get_retrieval], SYSTEM_PROMPT)
      │
      ├─ LLM decides → get_retrieval("definition of VARCHAR data type")
      │     │   WEAVIATE QUERY
      │     ├─ Retriever.hybrid_search(alpha=0.5, limit=20)
      │     │     _encode(query) → 768-d           (EMBED ENCODE)
      │     │     collection.query.hybrid(BM25 + vector)  (WEAVIATE HYBRID QUERY)
      │     │     → 20 candidates                   (WEAVIATE HITS: 20)
      │     ├─ CohereReranker.rerank(top_k=5)       (COHERE RERANK)
      │     │     → best 5 with rerank_score        (RERANKED top-5)
      │     └─ json.dumps(5 chunks) → back to LLM   (RETRIEVAL TOOL | N ms)
      │
      ├─ LLM writes answer strictly from the 5 chunks + citation
      └─ stream answer tokens → rag_model → main → terminal
          AGENT TURN COMPLETE | ANSWER GROUNDED | RAG TURN | N ms
```

---

## 8. Tuning Knobs — `rag/constant.py`

| Constant | Value | Effect on query |
|---|---|---|
| `MODEL` / `TEMPERATURE` | `gpt-4.1-mini` / `0.5` | the answering LLM |
| `HYBRID_SEARCH_ALPHA` | `0.5` | 0 = pure BM25 keyword, 1 = pure vector semantic |
| `RETRIEVAL_CANDIDATES` | `20` | chunks hybrid search returns (recall stage) |
| `RERANK_TOP_K` | `5` | chunks surviving rerank → sent to LLM (precision stage) |
| `DEFAULT_MAX_ITERATION` | `5` | × 2 + 1 = `11` recursion limit on the tool↔LLM loop |
| `COHERE_RERANK_MODEL` | `rerank-english-v3.0` | the reranker |

---

## 9. Reading the Logs (`logs/rag.log`)

One query turn, top to bottom:

```
RAG TURN START | input='...'              pipeline — question received
AGENT INVOKED | model=... | message='...' agent — turn begins
WEAVIATE QUERY: '...'                     tool — refined query the LLM chose
EMBED ENCODE | N ms                       search — query → 768-d vector
WEAVIATE HYBRID QUERY | N ms              search — BM25 + vector DB call
WEAVIATE HITS: 20 chunks ... sources=[…]  tool — candidates returned
COHERE RERANK | N ms                      rerank — Cohere call
RERANKED top-5 ...                        tool — final grounding sent to LLM
RETRIEVAL TOOL | N ms                     tool — total retrieval time
AGENT TURN | N ms                         agent — LLM streaming time
AGENT TURN COMPLETE | streamed_chars=N    agent — answer length
ANSWER GROUNDED   (or  NO RETRIEVAL)      agent — did it use the DB?
RAG TURN | N ms                           pipeline — whole-turn wall time
```

Use the `| N ms` lines to localize a slow turn: embed vs Weaviate vs Cohere vs LLM generation.

The ingestion side (PDF → stored chunk) is documented in `INJECTION_FLOW.md`.
