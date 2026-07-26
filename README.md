# RAG_MODEL

A Retrieval-Augmented Generation (RAG) agent over a Weaviate vector store. It answers
questions **strictly from indexed documents** — if the answer is not in the retrieved
context, it replies `"I don't know based on the provided documents."`

The agent is built on **LangChain** (`create_agent`), so the chat LLM provider is
swappable via a single config value.

## Architecture

```
User ──► src/llm/main.py (REPL)
            └─► pipeline.rag_model(chat_history, user_input)
                  └─► RagAgent  (LangChain create_agent)
                        ├─ LLM: init_chat_model(provider=PROVIDER)   # OpenAI by default
                        └─ tool: get_retrieval(query)
                              ├─ Retriever.hybrid_search  ── Weaviate (vector + BM25)
                              └─ CohereReranker.rerank     ── Cohere rerank-english-v3.0
```

- **Backend** (`src/backend/`): Weaviate client, `Document` / `DocumentChunk` schemas,
  document-registry seeding.
- **LLM / RAG** (`src/llm/`): multimodal PDF ingestion, the agent, retrieval tool,
  hybrid search, reranking, embeddings.

**Ingestion flow** (multimodal): PDF → `unstructured` hi_res parse (text / tables /
images) with Tesseract OCR fallback for text-less pages → image blocks described by a
vision LLM → structured chunking → embed → Weaviate `DocumentChunk`.

**Retrieval flow:** embed query → Weaviate hybrid search (top 20) → Cohere rerank
(top 5) → agent answers grounded in those chunks.

## Prerequisites

- **Python 3.11** (see platform note below)
- [uv](https://docs.astral.sh/uv/) for dependency management
- **Docker** — to run Weaviate locally (the app connects to `localhost:8080`)
- **System libraries** for `unstructured` hi_res parsing + OCR:
  ```bash
  brew install tesseract poppler      # macOS
  # Debian/Ubuntu: sudo apt-get install tesseract-ocr poppler-utils
  ```
- API keys: **OpenAI** (chat + vision image descriptions), **Cohere** (reranking)

### Platform note (Intel macOS)
On Intel macOS with Python 3.13 there are no `torch` wheels, so this project pins
Python 3.11 and `torch==2.2.2`, `transformers<5`, `sentence-transformers<4`, `numpy<2`.
On Linux or Apple-Silicon you can relax these and use a newer stack.

## Setup

1. **Clone & install**
   ```bash
   uv sync
   ```

2. **Environment** — create a `.env` in the project root:
   ```dotenv
   OPENAI_API_KEY=sk-...
   COHERE_API_KEY=...
   WEAVIATE_URL=http://localhost:8080
   EMBEDDING_MODEL_NAME=sentence-transformers/all-mpnet-base-v2
   LOG_LEVEL=INFO

   # Optional — Weaviate collection names (defaults shown)
   DOCUMENT_COLLECTION=Document
   CHUNK_COLLECTION=DocumentChunk
   ```

3. **Start Weaviate** (local, Docker):
   ```bash
   docker run -d --name weaviate -p 8080:8080 -p 50051:50051 \
     -e PERSISTENCE_DATA_PATH=/var/lib/weaviate \
     -e DEFAULT_VECTORIZER_MODULE=none \
     -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
     cr.weaviate.io/semitechnologies/weaviate:latest
   ```
   Verify it's ready: `curl http://localhost:8080/v1/.well-known/ready` → `200`.

4. **Create collections & seed the document registry** — creates the `Document` /
   `DocumentChunk` collections and seeds the source-document list (`src/backend/seed.py`):
   ```bash
   uv run python -m src.backend.main
   ```

5. **Ingest PDFs** — parse, chunk, embed, and index a folder of PDFs into the
   `DocumentChunk` collection:
   ```bash
   uv run python -m src.llm.rag.injection.load_pdf <folder>
   ```
   - `<folder>` is a directory of `.pdf` files (e.g. `IP/`, matching `seed.py`).
   - Re-runs skip unchanged files (sha256 manifest in `.ingest_manifest.json`).
   - Add `--reset` to drop + recreate `DocumentChunk` and force a clean re-ingest:
     ```bash
     uv run python -m src.llm.rag.injection.load_pdf IP --reset
     ```
   - Cropped image blocks are written under `images/<pdf-name>/`.

## Run

Start the interactive RAG agent:
```bash
uv run python -m src.llm.main
```
```
Welcome to the Rag model. Type 'exit' to quit.
You: <your question>
Assistant: <answer grounded in retrieved documents>
```
Type `exit` or `quit` to leave.

## Switching LLM provider

The chat model is provider-agnostic via `init_chat_model`. To switch:

1. Edit `PROVIDER` (and `MODEL`) in `src/llm/rag/constant.py`:
   ```python
   PROVIDER = "anthropic"      # openai | anthropic | google_genai | ...
   MODEL = "claude-..."
   ```
2. Install that provider's integration and set its API key:
   ```bash
   uv add langchain-anthropic
   ```

The agent, retrieval tool, and pipeline need no changes. The same `PROVIDER`/`MODEL`
also drives **vision image descriptions** during ingestion, so the chosen model must be
multimodal. **Reranking stays on Cohere** (a separate service, not part of the
chat-model abstraction).

## Project layout

```
src/
├── llm/
│   ├── main.py                     # interactive REPL entry point
│   ├── config.py                   # env config (RAGConfig)
│   └── rag/
│       ├── pipeline.py             # rag_model() entry
│       ├── constant.py             # PROVIDER / MODEL / retrieval + ingest tuning
│       ├── injection/              # ingestion: parse, describe_image, load_pdf
│       ├── chunking/               # structured_chunker.py
│       ├── embeddings/             # embedding model loader
│       ├── retrieval/              # search.py (Weaviate), rerank.py (Cohere)
│       └── rag_agent/
│           ├── agent.py            # RagAgent — LangChain create_agent
│           ├── prompt.py           # system prompt (strict, grounded)
│           └── tools/make_retrieval.py   # @tool: hybrid search + rerank
└── backend/
    ├── main.py                     # create collections + seed Document registry
    ├── config.py                   # env config (Config)
    ├── seed.py                     # source document list
    ├── models/                     # Document / DocumentChunk schemas
    └── weaviate_I/                 # Weaviate client
```
