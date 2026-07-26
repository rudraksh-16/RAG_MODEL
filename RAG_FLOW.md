# RAG_MODEL — How It Works

This document explains the end-to-end flow of the RAG system: how PDFs become
searchable knowledge (ingestion) and how a user question becomes a grounded,
cited answer (query). It also maps every log line you see in `logs/rag.log`.

---

## 1. Big Picture

There are **two independent pipelines**, run as separate processes:

```
INGEST  (offline, run once per corpus)
  PDFs ──► parse ──► chunk (+describe images) ──► embed ──► Weaviate

QUERY   (interactive, run per question)
  question ──► agent ──► retrieve (hybrid search ──► rerank) ──► grounded answer
```

Shared state lives in **Weaviate** (vector DB). Ingest writes to it; query reads from it.

| Layer | Tech | Where |
|---|---|---|
| Vector DB | Weaviate (`DocumentChunk` collection), HTTP `:8080` + gRPC `:50051` | `src/backend/weaviate_I/` |
| Embedder | `all-mpnet-base-v2` (SentenceTransformer, 768-d) | `src/llm/rag/embeddings/model.py` |
| Reranker | Cohere `rerank-english-v3.0` | `src/llm/rag/retrieval/rerank.py` |
| LLM | `gpt-4.1-mini` (temp 0.5) via LangChain `init_chat_model` | `src/llm/rag/rag_agent/agent.py` |
| Agent | LangChain `create_agent` with one tool | `src/llm/rag/rag_agent/` |

---

## 2. Ingestion Pipeline (offline)

Entry point: `python -m src.llm.rag.injection.load_pdf <folder> [--reset]`
Driver: `ingest_folder()` in `src/llm/rag/injection/load_pdf.py`.

Per PDF (`_process_pdf`):

1. **Parse** — `parse_pdf(path, image_dir)` (`injection/parse.py`) splits the PDF into
   *elements*: text blocks, tables, and extracted image files.
2. **Chunk** — `build_chunks(elements, source_file, describe_image=...)`
   (`chunking/structured_chunker.py`) turns elements into chunk objects. Each chunk
   carries `text, source_file, page_number, element_type, section, image_path`.
   - For **image** elements, `describe_image()` (`injection/describe_image.py`) calls a
     vision model to produce a text *description* — that description becomes the chunk
     text, so figures become searchable.
3. **Embed** — `_store_chunks()` encodes every chunk's text with the SentenceTransformer
   in one batch.
4. **Store** — batch-insert into the Weaviate `DocumentChunk` collection
   (batch size `RAGConstant.INGEST_BATCH_SIZE = 50`), vector + properties together.

Resilience details:
- **Manifest** (`.ingest_manifest.json`): sha256 per file. Unchanged files are skipped
  on re-run. `--reset` drops + recreates the collection and clears the manifest.
- A broken PDF is logged and skipped — it never aborts the whole run.

Result of a full run: 8 PDFs → ~890 chunks (≈580 image, 185 text, 125 table).

---

## 3. Query Pipeline (interactive)

Entry point: `python -m src.llm.main`.

### 3.1 CLI loop — `src/llm/main.py`
1. **Warm-up** (startup, once): `get_embedding_model()` + `get_client()` so the first
   question doesn't pay model-load / connection cost.
2. Read-eval loop: take input, append to `chat_history`, stream the answer token-by-token.
3. On exit: `close_client()` closes Weaviate cleanly.

### 3.2 Pipeline turn — `pipeline.py: rag_model()`
A generator. Builds a `RagAgent`, streams its output back to the CLI, logs the turn
duration. Failures are caught and logged so the loop degrades gracefully.

### 3.3 The agent — `rag_agent/agent.py: RagAgent.stream()`
- Built with LangChain `create_agent(llm, tools=[get_retrieval], system_prompt=...)`.
- The LLM **decides** whether to call the `get_retrieval` tool. The system prompt
  (`rag_agent/prompt.py`) instructs it to retrieve before answering and to cite sources.
- `recursion_limit = max_iteration * 2 + 1` (default 11) bounds the tool↔LLM loop.
- Streams in `stream_mode="messages"`: raw tool payloads are skipped, only the LLM's
  answer tokens are yielded. A flag records whether retrieval actually happened.

> **Note:** the agent costs one LLM round trip to *decide* to retrieve, then a second to
> *answer*. That extra hop is the main latency cost — see `wiki/meta/RAG Latency Optimization.md`.

### 3.4 The retrieval tool — `rag_agent/tools/make_retrieval.py: get_retrieval(query)`
Called by the LLM with a refined query. Steps:

1. **Hybrid search** — `Retriever.hybrid_search()` (`retrieval/search.py`):
   - encode the query into a 768-d vector,
   - Weaviate `hybrid` query = **BM25 keyword + vector semantic**, blended by
     `alpha=0.5`, returning the top `RETRIEVAL_CANDIDATES = 20` chunks.
2. **Rerank** — `CohereReranker.rerank()` (`retrieval/rerank.py`):
   - Cohere reorders the 20 candidates by true relevance to the query,
   - keeps the top `RERANK_TOP_K = 5`.
3. Return the 5 reranked chunks as JSON → fed back to the LLM as grounding.

### 3.5 Answer
The LLM writes the final answer from the 5 grounding chunks and streams it to the
terminal token-by-token.

---

## 4. Tuning Knobs — `rag/constant.py`

| Constant | Value | Effect |
|---|---|---|
| `MODEL` / `TEMPERATURE` | `gpt-4.1-mini` / `0.5` | answer LLM |
| `HYBRID_SEARCH_ALPHA` | `0.5` | 0 = pure BM25, 1 = pure vector |
| `RETRIEVAL_CANDIDATES` | `20` | how many chunks hybrid search returns |
| `RERANK_TOP_K` | `5` | how many survive rerank → sent to LLM |
| `DEFAULT_MAX_ITERATION` | `5` | agent loop bound (× 2 + 1 = recursion limit) |
| `INGEST_BATCH_SIZE` | `50` | Weaviate insert batch size |

---

## 5. Reading the Logs (`logs/rag.log`)

Every query turn writes a timed trace (file-only, format
`time | LEVEL | logger | message`). One turn, top to bottom:

```
RAG TURN START | input='...'              pipeline — question received
AGENT INVOKED | model=... | message='...' agent — turn begins
WEAVIATE QUERY: '...'                     tool — refined query the LLM chose
EMBED ENCODE | N ms                       search — query → vector
WEAVIATE HYBRID QUERY | N ms              search — BM25+vector DB call
WEAVIATE HITS: 20 chunks ... sources=[…]  tool — candidates returned
COHERE RERANK | N ms                      rerank — Cohere call
RERANKED top-5 ...                        tool — final grounding sent to LLM
RETRIEVAL TOOL | N ms                     tool — total retrieval time
AGENT TURN | N ms                         agent — LLM streaming time
AGENT TURN COMPLETE | streamed_chars=N    agent — answer length
ANSWER GROUNDED  (or  NO RETRIEVAL)       agent — did it use the DB?
RAG TURN | N ms                           pipeline — whole-turn wall time
```

Use the `| N ms` lines to see where a slow turn spent its time: embed vs Weaviate
vs Cohere vs LLM generation.

---

## 6. Performance Notes

- Weaviate client and embedding model are **module-level singletons** — built once,
  reused across turns (`weaviate_I/client.py`, `embeddings/model.py`).
- First-turn cold start is moved to startup warm-up in `main.py`.
- Open optimizations (deferred): drop the agent's decide-to-retrieve hop for direct
  retrieval; reuse the Cohere client as a singleton; smaller/faster embed model.
  See `wiki/meta/RAG Latency Optimization.md`.
