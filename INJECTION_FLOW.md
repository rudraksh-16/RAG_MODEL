# Injection Flow — PDF to Stored Chunk (Detailed Walkthrough)

This document traces the **ingestion (injection) pipeline** end to end: every function
that runs, in order, from a raw PDF on disk to embedded vectors sitting in Weaviate.
It follows one concrete example page so each transformation is visible.

Entry point: `python -m src.llm.rag.injection.load_pdf <folder> [--reset]`

Files involved:

| Step | File | Function |
|---|---|---|
| Driver / orchestration | `src/llm/rag/injection/load_pdf.py` | `ingest_folder` → `_process_pdf` |
| Parse PDF → elements | `src/llm/rag/injection/parse.py` | `parse_pdf` |
| Image → text description | `src/llm/rag/injection/describe_image.py` | `describe_image` |
| Elements → chunks | `src/llm/rag/chunking/structured_chunker.py` | `build_chunks` |
| Embed + store | `src/llm/rag/injection/load_pdf.py` | `_store_chunks` |
| Schema | `src/backend/models/document_chunk.py` | `initialize_document_chunk_collection` |
| Embedder | `src/llm/rag/embeddings/model.py` | `get_embedding_model` |
| Constants | `src/llm/rag/constant.py` | `RAGConstant` |

---

## 0. The Example

Suppose `IP/` holds one PDF, `leip101.pdf`, and page 4 contains:

```
┌──────────────────────────────────────────────┐
│  Data Types in MySQL              ← heading    │
│                                                │
│  MySQL supports several data types grouped     │  ← paragraph
│  into numeric, string, and date/time...        │
│                                                │
│  ┌─────────────┬───────────────┐               │
│  │ Type        │ Description    │   ← a table   │
│  ├─────────────┼───────────────┤               │
│  │ INT         │ whole numbers  │               │
│  │ VARCHAR(n)  │ text up to n   │               │
│  └─────────────┴───────────────┘               │
│                                                │
│  [ Figure 4.1: ER diagram of a student DB ]    │  ← an image
└──────────────────────────────────────────────┘
```

We run:

```bash
python -m src.llm.rag.injection.load_pdf IP --reset
```

We follow this one page through the whole pipeline.

---

## 1. Driver Setup — `ingest_folder()`

```
ingest_folder("IP", reset=True)
```

1. `get_client()` — open the Weaviate client (module-level singleton).
2. `get_embedding_model()` — load `all-mpnet-base-v2` (768-d SentenceTransformer).
3. Because `reset=True`:
   - `initialize_document_chunk_collection(client, recreate=True)` **drops and recreates**
     the `DocumentChunk` collection so the V2 schema (with multimodal metadata) is clean.
   - Manifest reset to `{}` and written to `.ingest_manifest.json`.
   (Without `--reset`: collection is created only if missing, and the existing manifest is
   loaded so unchanged files can be skipped.)
4. `collection = client.collections.use("DocumentChunk")` — handle to write into.
5. `_list_pdfs("IP")` → `["IP/leip101.pdf"]` (sorted, `.pdf` only).

### Per-file loop (skip logic)

For `IP/leip101.pdf`:

- `_file_hash(path)` → sha256 of the file bytes (read in 64 KB blocks).
- If `manifest[path] == hash` → **SKIP** (file unchanged since last ingest). With `--reset`
  the manifest is empty, so it never skips.
- Otherwise call `_process_pdf(...)`. On success, record the hash in the manifest and save
  it immediately (so a crash mid-run doesn't force re-ingesting completed files).
- Any exception in one PDF is caught, logged as `FAILED`, and the loop continues to the next
  file — one broken document never aborts the whole run.

At the end, `_report(summary)` prints counts: ok / skipped / empty / failed.
`finally: client.close()`.

---

## 2. Parse — `parse_pdf(path, image_dir)`

`image_dir` = `images/leip101` (derived from the source filename, no extension).

### 2.1 Layout-aware partition

```python
elements = partition_pdf(
    filename=file_path,
    strategy="hi_res",                  # layout-model detection, not raw text dump
    infer_table_structure=True,         # tables come back with HTML in metadata
    extract_image_block_types=["Image"],
    extract_image_block_output_dir=image_output_dir,  # crops images to disk
)
```

`unstructured`'s `hi_res` strategy runs a layout model that classifies regions on each page.
For our example page 4, it returns typed **`Element`** objects roughly like:

| `category` | `text` | key metadata |
|---|---|---|
| `Title` | `"Data Types in MySQL"` | `page_number=4` |
| `NarrativeText` | `"MySQL supports several data types..."` | `page_number=4` |
| `Table` | `"Type Description INT ..."` | `page_number=4`, `text_as_html="<table>…</table>"` |
| `Image` | `""` (no text) | `page_number=4`, `image_path="images/leip101/figure-4-1.jpg"` |

The image region is **cropped and saved as a file** to `images/leip101/`, and its path is
stored on `element.metadata.image_path`. The pixels are not text yet — that happens in step 3.

### 2.2 OCR fallback (scanned / image-only pages)

```python
covered = _pages_with_text(elements)   # pages that yielded real non-image text
missing = [pages with no text layer at all]
if missing:
    ocr_elements = partition_pdf(file_path, strategy="ocr_only")  # Tesseract
    # keep only recovered elements on the missing pages that actually have text
    elements.extend(recovered)
```

- `_pages_with_text()` collects page numbers that produced non-`Image` text.
- `_total_pages()` reads the real page count via `pypdf.PdfReader`.
- Any page in neither set (e.g. a fully scanned page where `hi_res` found no text layer) is
  re-parsed with `strategy="ocr_only"` (Tesseract OCR), and only the text-bearing recovered
  elements on those pages are appended.

Result: a flat `List[Element]` covering every page. Logged as `PARSED <file> -> N elements`.

> You can run just this step to inspect it:
> `python -m src.llm.rag.injection.parse IP/leip101.pdf images/_debug`
> It prints the element count, a by-category breakdown, and one line per element.

---

## 3. Chunk — `build_chunks(elements, source_file, describe_image=describe_image)`

This converts typed elements into a uniform `Chunk` contract. **Each element type takes a
different path**, and they all collapse into the same dataclass:

```python
@dataclass
class Chunk:
    text: str                  # the ONLY field that gets embedded + searched
    source_file: str
    page_number: Optional[int]
    element_type: str          # "text" | "table" | "image"
    section: Optional[str] = None
    image_path: Optional[str] = None
```

### 3.1 Single pass over elements (split by type)

```python
for el in elements:
    if el.category == "Table":   → make a table Chunk immediately
    elif el.category == "Image": → describe via vision LLM, make an image Chunk
    else:                        → defer into text_elements[] for grouping
```

**Table** (`"Data Types in MySQL"` table):
- `text = el.metadata.text_as_html` (falls back to plain `el.text`). Keeping the **HTML**
  means rows and columns survive, so the table stays meaningful after embedding.
- `element_type="table"`, `section=None`.

**Image** (`figure-4-1.jpg`):
- `image_path = el.metadata.image_path`.
- Only if a `describe_image` callback is supplied AND a path exists:
  `description = describe_image(image_path)` (see §4).
- If the description is non-empty, make `element_type="image"` Chunk whose **`text` is the
  vision description** — that is what makes a figure searchable. Empty description → image
  silently skipped (no chunk).

**Everything else** (`Title`, `NarrativeText`, lists, headers) is collected into
`text_elements` for structure-aware grouping next.

### 3.2 Group text under headings — `chunk_by_title`

```python
composites = chunk_by_title(
    text_elements,
    max_characters=1000,            # hard cap per chunk
    new_after_n_chars=800,          # soft cap: start a new chunk after this
    combine_text_under_n_chars=200, # merge tiny fragments together
)
```

`unstructured.chunking.title.chunk_by_title` groups consecutive text under its nearest
heading **without cutting mid-section**, respecting the size limits above. Our `Title`
+ `NarrativeText` become one composite chunk.

For each composite:
- `text = comp.text`
- `element_type="text"`
- `section = _section_of(comp)` — scans the composite's `orig_elements` for the first
  `Title`/`Header` and uses its text (here `"Data Types in MySQL"`). This records *which
  section* the chunk came from, used later for citation.

### 3.3 Result for our page

Three chunks from page 4:

```
Chunk(text="<table><tr><td>Type</td>...</table>", element_type="table", page=4, section=None)
Chunk(text="<vision description of the ER diagram...>", element_type="image", page=4,
      image_path="images/leip101/figure-4-1.jpg")
Chunk(text="Data Types in MySQL\nMySQL supports several data types...", element_type="text",
      page=4, section="Data Types in MySQL")
```

Logged as `CHUNKED <file> -> N chunks {'text': .., 'table': .., 'image': ..}`.

---

## 4. Image → Text — `describe_image(image_path)`

Called from the chunker for each `Image` element. This is how figures become searchable text.

```python
with open(image_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()       # read crop, base64-encode

message = HumanMessage(content=[
    {"type": "text", "text": _PROMPT},              # "Describe this image in detail..."
    {"type": "image_url",
     "image_url": {"url": f"data:{mime};base64,{b64}"}},
])
response = _get_model().invoke([message])           # gpt-4.1-mini, temperature=0
return text.strip()
```

- `_get_model()` lazily builds the multimodal LLM **once** (`init_chat_model(MODEL, PROVIDER,
  temperature=0)` → `gpt-4.1-mini` / `openai`) and reuses it for every image.
- `_mime()` picks `image/png` vs `image/jpeg` from the file extension.
- The vision model returns prose like *"An entity-relationship diagram showing a Student
  entity with attributes roll_no, name... linked to a Course entity..."*. **That prose
  becomes the chunk's `text`.**
- **Failure is swallowed**: any exception → log a warning, return `""`. The chunker then skips
  that image instead of crashing the whole ingest. This is why image counts can be lower than
  the number of image files on disk.

---

## 5. Embed + Store — `_store_chunks(chunks, source_file, collection, embedding_model)`

### 5.1 Embed (one batch per PDF)

```python
embeddings = embedding_model.encode([c.text for c in chunks])
```

- Every chunk's `text` (table HTML, vision description, or grouped paragraph — all are now
  just strings) is encoded in a **single batched call** for the whole document.
- Output: one 768-dimensional float vector per chunk (`all-mpnet-base-v2`).

### 5.2 Insert into Weaviate

```python
with collection.batch.fixed_size(RAGConstant.INGEST_BATCH_SIZE) as batch:  # 50
    for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
        batch.add_object(
            properties={
                "chunk_text":   chunk.text,
                "document_id":  source_file,
                "chunk_index":  idx,
                "deleted_at":   None,
                "source_file":  chunk.source_file,
                "page_number":  chunk.page_number,
                "element_type": chunk.element_type,
                "section":      chunk.section,
                "image_path":   chunk.image_path,
            },
            vector=vector.tolist(),
        )
```

- Objects are flushed in batches of `INGEST_BATCH_SIZE = 50`.
- **Vector and properties are stored together**: the vector powers semantic search;
  `chunk_text` powers BM25 keyword search; the rest is metadata returned at query time for
  citations (which file, page, section, element type, and original image path).
- `chunk_index` is the chunk's position within the document.

### 5.3 The target schema — `DocumentChunk`

Created by `initialize_document_chunk_collection`:

- Vector index: **HNSW**, `distance_metric=COSINE`, `ef_construction=128`, `max_connections=32`.
- Vectors are **provided manually** (we embed ourselves; Weaviate does not vectorize).
- Properties: `chunk_text`, `document_id`, `chunk_index`, `deleted_at`, and the V2
  multimodal set: `source_file`, `page_number`, `element_type`, `section`, `image_path`.

For our page 4, three rows land in the collection (text / table / image), each with its
768-d vector and the metadata above.

---

## 6. Full Sequence (one PDF)

```
ingest_folder("IP", reset=True)
│
├─ get_client()                          → Weaviate singleton
├─ get_embedding_model()                 → all-mpnet-base-v2 (768-d)
├─ initialize_document_chunk_collection(recreate=True)   → fresh DocumentChunk schema
│
└─ _process_pdf("IP/leip101.pdf", "leip101.pdf", ...)
   │
   ├─ parse_pdf(path, "images/leip101")
   │     partition_pdf(hi_res, tables=HTML, images→disk)   → List[Element]
   │     OCR fallback for pages with no text layer
   │
   ├─ build_chunks(elements, "leip101.pdf", describe_image)
   │     Table   → Chunk(text=HTML,        type="table")
   │     Image   → describe_image()  → Chunk(text=description, type="image")
   │     Text    → chunk_by_title()  → Chunk(text=grouped,     type="text", section=…)
   │
   └─ _store_chunks(chunks, ...)
         embedding_model.encode([chunk.text ...])           → 768-d vectors
         collection.batch.add_object(properties + vector)   → Weaviate (batch=50)
```

A full real run: 8 PDFs → ~890 chunks (≈580 image, 185 text, 125 table).

---

## 7. Where to Look / How to Re-run

| Want to... | Command |
|---|---|
| Full clean re-ingest | `python -m src.llm.rag.injection.load_pdf IP --reset` |
| Incremental (skip unchanged) | `python -m src.llm.rag.injection.load_pdf IP` |
| Inspect parse output only | `python -m src.llm.rag.injection.parse IP/leip101.pdf images/_debug` |
| Inspect chunk output only | `python -m src.llm.rag.chunking.structured_chunker IP/leip101.pdf` |
| Describe a single image | `python -m src.llm.rag.injection.describe_image images/leip101/figure-4-1.jpg` |

State on disk after a run:
- `images/<doc>/…` — cropped image files referenced by image chunks.
- `.ingest_manifest.json` — sha256 per ingested file (drives skip-on-unchanged).
- Weaviate `DocumentChunk` collection — the embedded, queryable chunks.

The query side (question → answer) is documented in `RAG_FLOW.md` §3.
