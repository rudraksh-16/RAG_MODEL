import re
from typing import List

from pypdf import PdfReader

from src.backend.weaviate_I.client import get_client
from src.llm.logger import get_logger
from src.llm.rag.chunking.text_chunker import chunk_text
from src.llm.rag.embeddings.model import get_embedding_model

logger = get_logger("rag.ingest")


def extract_text_from_pdf(file_path: str) -> str:
    text_parts = []

    with open(file_path, "rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    text = " ".join(text_parts)
    text = re.sub(r"\s+", " ", text)
    text = "".join(c for c in text if c.isprintable())

    return text.strip()


def get_documents_without_chunks(client) -> List[dict]:
    document_collection = client.collections.use("Document")
    chunk_collection = client.collections.use("DocumentChunk")

    documents = document_collection.query.fetch_objects(
        return_properties=["document_path"]
    )
    chunks = chunk_collection.query.fetch_objects(return_properties=["document_id"])

    chunked_doc_ids = {obj.properties["document_id"] for obj in chunks.objects}

    return [
        {
            "document_id": str(doc.uuid),
            "document_path": doc.properties["document_path"],
        }
        for doc in documents.objects
        if str(doc.uuid) not in chunked_doc_ids
    ]


def ingest_documents():
    client = get_client()
    embedding_model = get_embedding_model()

    try:
        chunk_collection = client.collections.use("DocumentChunk")
        documents = get_documents_without_chunks(client)
        logger.info("INGEST START: %d document(s) without chunks", len(documents))

        for doc in documents:
            path = doc["document_path"]
            logger.info("INGESTING: %s", path)

            try:
                text = extract_text_from_pdf(path)
            except FileNotFoundError:
                logger.warning("File not found, skipping: %s", path)
                continue
            except Exception as e:
                logger.warning("Failed to read %s: %s", path, e)
                continue

            if not text.strip():
                logger.warning("Empty content, skipping: %s", path)
                continue

            chunks = chunk_text(text)
            embeddings = embedding_model.encode(chunks)

            with chunk_collection.batch.fixed_size(50) as batch:
                for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
                    batch.add_object(
                        properties={
                            "chunk_text": chunk,
                            "document_id": doc["document_id"],
                            "chunk_index": idx,
                            "deleted_at": None,
                        },
                        vector=vector.tolist(),
                    )

            logger.info("STORED %d chunks into Weaviate for %s", len(chunks), path)

    finally:
        client.close()


if __name__ == "__main__":
    ingest_documents()
