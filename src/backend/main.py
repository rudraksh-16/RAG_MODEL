import weaviate

from src.backend.models.document import initialize_document_collection
from src.backend.models.document_chunk import initialize_document_chunk_collection
from src.backend.seed import seed_documents
from src.llm.logger import get_logger

logger = get_logger("backend.setup")


def main() -> None:
    """Create the Document/DocumentChunk schemas and seed the Document collection."""
    client = weaviate.connect_to_local()
    try:
        initialize_document_collection(client)
        initialize_document_chunk_collection(client)
        seed_documents(client)

        logger.info("Collections: %s", client.collections.list_all())
        docs = client.collections.use("Document").query.fetch_objects()
        for d in docs.objects:
            logger.info("Document: %s", d.properties)
    finally:
        client.close()


if __name__ == "__main__":
    main()
