import hashlib
import json
import os
import sys
from collections import Counter
from typing import List

from src.backend.config import Config
from src.backend.models.document_chunk import initialize_document_chunk_collection
from src.backend.weaviate_I.client import get_client
from src.llm.logger import get_logger
from src.llm.rag.chunking.structured_chunker import build_chunks
from src.llm.rag.constant import RAGConstant
from src.llm.rag.embeddings.model import get_embedding_model
from src.llm.rag.injection.describe_image import describe_image
from src.llm.rag.injection.parse import parse_document

logger = get_logger("rag.ingest")

MANIFEST_PATH = ".ingest_manifest.json"
IMAGE_ROOT = "images"


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _load_manifest() -> dict:
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {}


def _save_manifest(manifest: dict) -> None:
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def _list_documents(folder: str) -> List[str]:
    return sorted(
        os.path.join(folder, name)
        for name in os.listdir(folder)
        if name.lower().endswith(RAGConstant.SUPPORTED_EXTENSIONS)
    )


def _report(summary: List[dict]) -> None:
    by_status = Counter(s["status"] for s in summary)
    logger.info(
        "INGEST SUMMARY: %d ok, %d skipped, %d empty, %d failed (of %d)",
        by_status.get("ok", 0),
        by_status.get("skipped", 0),
        by_status.get("empty", 0),
        by_status.get("failed", 0),
        len(summary),
    )
    for s in summary:
        if s["status"] == "ok":
            logger.info(
                "  OK %s: %d chunks (text=%d, tables=%d, images=%d) from %d elements",
                s["file"], s["chunks"], s["text"], s["tables"], s["images"], s["elements"],
            )
        elif s["status"] == "failed":
            logger.warning("  FAILED %s: %s", s["file"], s.get("error"))


def _store_chunks(chunks: List, source_file: str, collection, embedding_model) -> None:
    """Embed chunks and batch-insert them into the chunk collection."""
    embeddings = embedding_model.encode([c.text for c in chunks])
    with collection.batch.fixed_size(RAGConstant.INGEST_BATCH_SIZE) as batch:
        for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            batch.add_object(
                properties={
                    "chunk_text": chunk.text,
                    "document_id": source_file,
                    "chunk_index": idx,
                    "deleted_at": None,
                    "source_file": chunk.source_file,
                    "page_number": chunk.page_number,
                    "element_type": chunk.element_type,
                    "section": chunk.section,
                    "image_path": chunk.image_path,
                },
                vector=vector.tolist(),
            )


def _process_document(path: str, source_file: str, collection, embedding_model) -> dict:
    """Parse, chunk, and store one document (PDF/DOCX/TXT). Returns its summary entry."""
    image_dir = os.path.join(IMAGE_ROOT, os.path.splitext(source_file)[0])
    elements = parse_document(path, image_dir)
    chunks = build_chunks(elements, source_file, describe_image=describe_image)

    if not chunks:
        logger.warning("No chunks produced, skipping: %s", source_file)
        return {"file": source_file, "status": "empty"}

    _store_chunks(chunks, source_file, collection, embedding_model)

    counts = Counter(c.element_type for c in chunks)
    logger.info(
        "STORED %d chunks for %s (text=%d, tables=%d, images=%d)",
        len(chunks), source_file,
        counts.get("text", 0), counts.get("table", 0), counts.get("image", 0),
    )
    return {
        "file": source_file,
        "status": "ok",
        "elements": len(elements),
        "chunks": len(chunks),
        "text": counts.get("text", 0),
        "tables": counts.get("table", 0),
        "images": counts.get("image", 0),
    }


def ingest_folder(folder: str, reset: bool = False) -> None:
    """Ingest every PDF in a folder through the V2 multimodal front end.

    reset=True drops + recreates DocumentChunk (clean re-ingest) and clears the hash
    manifest. Otherwise unchanged files (matching sha256 in the manifest) are skipped.
    A broken document is logged and skipped; it never aborts the run.
    """
    client = get_client()
    embedding_model = get_embedding_model()

    if reset:
        initialize_document_chunk_collection(client, recreate=True)
        logger.info("RESET: DocumentChunk recreated with V2 schema")
        manifest: dict = {}
        _save_manifest(manifest)
    else:
        initialize_document_chunk_collection(client)
        manifest = _load_manifest()

    try:
        collection = client.collections.use(Config.CHUNK_COLLECTION)
        documents = _list_documents(folder)
        logger.info("INGEST START: %d document(s) in %s", len(documents), folder)

        summary: List[dict] = []
        for path in documents:
            source_file = os.path.basename(path)
            try:
                file_hash = _file_hash(path)
                if manifest.get(path) == file_hash:
                    logger.info("SKIP unchanged: %s", source_file)
                    summary.append({"file": source_file, "status": "skipped"})
                    continue

                logger.info("INGESTING: %s", source_file)
                result = _process_document(path, source_file, collection, embedding_model)
                summary.append(result)
                if result["status"] == "ok":
                    manifest[path] = file_hash
                    _save_manifest(manifest)
            except Exception as e:
                logger.error("FAILED %s: %s", source_file, e)
                summary.append({"file": source_file, "status": "failed", "error": str(e)})
                continue

        _report(summary)

    finally:
        client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python -m src.llm.rag.injection.load_pdf <folder> [--reset]  # ingests .pdf/.docx/.txt")
        raise SystemExit(1)
    target = sys.argv[1]
    reset_flag = "--reset" in sys.argv[2:]
    ingest_folder(target, reset=reset_flag)
