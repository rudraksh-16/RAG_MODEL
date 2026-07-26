# RAG_MODEL — Project Report

## 1. What This Project Is

**RAG_MODEL** is a Retrieval-Augmented Generation (RAG) system that answers natural-language
questions about a corpus of documents, grounding every answer strictly in the source material
and citing where each fact came from (file, page, and element type).

The distinguishing feature is that it is **multimodal at ingest time**: it does not just read the
plain text of a document. It also extracts **tables** (preserved as HTML so rows/columns survive)
and **images/figures** (converted into text descriptions by a vision model), so the system can
answer questions whose answers live in a diagram or a table — not only in the prose.

The reference corpus is an "Informatics Practices" textbook (SQL / MySQL), ingested as PDFs.

### Core guarantees
- **Grounded only:** the agent is instructed to answer *only* from retrieved documents; if the
  answer is not present, it replies with a fixed refusal sentence rather than hallucinating.
- **Cited:** every answer ends with `(source: <file>, page <n>, <text|table|image>)`.
- **Two front doors:** an interactive **CLI** and a **FastAPI web service** with a chat UI.

---

## 2. Architecture at a Glance

The codebase splits into two halves:

| Layer | Path | Responsibility |
|-------|------|----------------|
| **LLM / RAG core** | `src/llm/` | Ingestion, chunking, embeddings, retrieval, reranking, the agent |
| **Backend (Weaviate)** | `src/backend/` | Vector-DB client, collection schemas, seeding |
| **Web** | `src/web/` | FastAPI server + static chat UI |

There are two independent pipelines: an **offline ingest path** (documents → vector DB) and an
**online query path** (question → grounded answer).

### 2.1 Ingest path (offline)

```
document (.pdf / .docx / .txt)
   │
   ▼  parse.py  (unstructured)
typed elements  ── PDF: hi_res layout + OCR fallback + image extraction
   │                 tables → HTML,  images → cropped to disk
   ▼  structured_chunker.py
Chunks  ── text  (grouped under headings via chunk_by_title)
           table (HTML preserved)
           image (vision-model description via describe_image)
   │
   ▼  embeddings/model.py  (SentenceTransformer)
768-dim vectors
   │
   ▼  load_pdf.py → Weaviate
DocumentChunk collection (HNSW / cosine), batched inserts
```

Ingest is **incremental**: a SHA-256 manifest (`.ingest_manifest.json`) skips unchanged files;
`--reset` drops and recreates the collection for a clean re-ingest. A broken document is logged
and skipped — it never aborts the run.

### 2.2 Query path (online)

```
user question
   │
   ▼  RagAgent (LangChain create_agent, streaming)
LLM decides to call the retrieval tool
   │
   ▼  get_retrieval(query)  →  Retriever.hybrid_search
hybrid search = vector (semantic) + BM25 (keyword), alpha=0.5, 20 candidates
   │
   ▼  CohereReranker.rerank
Cohere rerank-english-v3.0 → top 5 most relevant chunks
   │
   ▼  LLM composes answer strictly from those 5 chunks
grounded, cited answer  (+ deduped source list on the web path)
```

---

## 3. Technology Stack

### 3.1 Language & tooling
- **Python ≥ 3.11**
- **uv** for dependency / environment management (`pyproject.toml`, `uv.lock`)

### 3.2 Core libraries

| Concern | Technology | Notes |
|---------|-----------|-------|
| **Agent framework** | LangChain + LangGraph | `create_agent`, `init_chat_model` — provider-agnostic |
| **LLM** | OpenAI `gpt-4.1-mini` | temperature 0.5, via `langchain-openai` |
| **Vector database** | Weaviate (`weaviate-client` v4) | `DocumentChunk` class, HNSW index, cosine distance |
| **Embeddings** | `sentence-transformers` | e.g. `all-mpnet-base-v2` (768-dim), configurable via env |
| **Reranking** | Cohere `rerank-english-v3.0` | top-k = 5 |
| **Document parsing** | `unstructured[pdf,docx]` | hi_res layout detection, table structure inference |
| **OCR** | `pytesseract` (Tesseract) | fallback for scanned / image-only pages |
| **PDF handling** | `pypdf`, `pdfminer.six` | page counting, text extraction |
| **Vision (figures)** | OpenAI vision (`describe_image`) | turns figures into searchable text descriptions |
| **Web API** | FastAPI + Uvicorn | `/api/chat` endpoint, static chat UI at `/` |
| **Config** | `python-dotenv` | secrets & tuning via `.env` |
| **ML runtime** | `torch` 2.2.2, `onnx` / `onnxruntime`, `transformers` | pinned for Intel-mac compatibility |

### 3.3 Retrieval & chunking tuning (`RAGConstant`)

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `HYBRID_SEARCH_ALPHA` | 0.5 | equal weight between vector and keyword search |
| `RETRIEVAL_CANDIDATES` | 20 | chunks pulled from Weaviate before reranking |
| `RERANK_TOP_K` | 5 | chunks kept after Cohere rerank, sent to the LLM |
| `CHUNK_MAX_CHARS` | 1000 | max chunk size |
| `CHUNK_NEW_AFTER_N_CHARS` | 800 | soft cut point |
| `CHUNK_COMBINE_UNDER_N_CHARS` | 200 | merge tiny fragments |
| `INGEST_BATCH_SIZE` | 50 | Weaviate batch insert size |
| `SUPPORTED_EXTENSIONS` | `.pdf`, `.docx`, `.txt` | accepted input formats |

---

## 4. Key Components (by module)

| Module | File | Role |
|--------|------|------|
| **Parsing** | `llm/rag/injection/parse.py` | Extension dispatch; PDF hi_res + OCR fallback + image extraction |
| **Image description** | `llm/rag/injection/describe_image.py` | Vision-model text description of figures |
| **Chunking** | `llm/rag/chunking/structured_chunker.py` | `Chunk` dataclass; heading-aware text, table-HTML, image chunks |
| **Embeddings** | `llm/rag/embeddings/model.py` | Build-once SentenceTransformer singleton |
| **Ingest orchestration** | `llm/rag/injection/load_pdf.py` | Parse → chunk → embed → store; manifest, batching, reset |
| **Retrieval** | `llm/rag/retrieval/search.py` | `Retriever`: vector + hybrid (BM25) search |
| **Reranking** | `llm/rag/retrieval/rerank.py` | `CohereReranker` |
| **Retrieval tool** | `llm/rag/rag_agent/tools/make_retrieval.py` | LangChain `@tool`; captures grounding sources |
| **Agent** | `llm/rag/rag_agent/agent.py` | `RagAgent`: builds LLM + tools, streams the answer |
| **System prompt** | `llm/rag/rag_agent/prompt.py` | Grounding rules, two-retrieval policy, citation format |
| **Pipeline** | `llm/rag/pipeline.py` | `rag_model()` — one streamed RAG turn, fail-safe |
| **CLI entry** | `llm/main.py` | Interactive REPL loop |
| **DB schemas** | `backend/models/document_chunk.py`, `document.py` | Weaviate collection definitions |
| **DB client** | `backend/weaviate_I/client.py` | Shared, build-once connected client |
| **Web server** | `web/server.py` | FastAPI `/api/chat` + static UI, warms models on startup |

---

## 5. How It Runs

**Ingest a corpus:**
```bash
uv run python -m src.llm.rag.injection.load_pdf <folder> --reset
```

**CLI chat:**
```bash
uv run python -m src.llm.main
```

**Web service:**
```bash
uv run uvicorn src.web.server:app
# → chat UI at http://localhost:8000/
```

**Required environment (`.env`):** `OPENAI_API_KEY`, `COHERE_API_KEY`, `WEAVIATE_URL`,
`EMBEDDING_MODEL_NAME`, `LOG_LEVEL` (optional).

---

## 6. Design Notes Worth Highlighting

- **Provider-agnostic LLM** — swapping the chat model is a one-line change in `RAGConstant`
  (`init_chat_model` handles the provider).
- **Build-once singletons** — the embedding model, Weaviate client, and Cohere client are each
  built once and reused across requests (latency optimization).
- **Fail-safe turns** — a failed RAG turn is logged and yields nothing, so the CLI/API degrade
  gracefully instead of crashing.
- **Grounding observability** — the agent logs whether an answer was actually backed by a
  retrieval call, flagging any answer produced without hitting the DB.
- **Strict anti-hallucination prompt** — the model must retrieve (twice if needed) and refuse
  with a fixed sentence when the corpus lacks the answer.
