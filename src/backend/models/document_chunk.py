from weaviate.classes.config import (
    Configure,
    Property,
    DataType,
    VectorDistances,
)

from src.backend.config import Config


def initialize_document_chunk_collection(client, recreate: bool = False) -> None:
    """
    DocumentChunk collection for RAG:
    - vectors provided manually
    - HNSW index enabled

    Set recreate=True for an intentional V2 re-ingest: drops the existing collection
    (and all chunks) so the multimodal-metadata schema is applied cleanly.
    """
    name = Config.CHUNK_COLLECTION

    if client.collections.exists(name):
        if not recreate:
            return
        client.collections.delete(name)

    client.collections.create(
        name=name,
        vector_index_config=Configure.VectorIndex.hnsw(
            distance_metric=VectorDistances.COSINE,
            ef_construction=128,
            max_connections=32,
        ),
        properties=[
            Property(
                name="chunk_text",
                data_type=DataType.TEXT,
            ),
            Property(
                name="document_id",
                data_type=DataType.TEXT,
            ),
            Property(
                name="chunk_index",
                data_type=DataType.INT,
            ),
            Property(
                name="deleted_at",
                data_type=DataType.DATE,
            ),
            # V2 multimodal metadata
            Property(
                name="source_file",
                data_type=DataType.TEXT,
            ),
            Property(
                name="page_number",
                data_type=DataType.INT,
            ),
            Property(
                name="element_type",
                data_type=DataType.TEXT,
            ),
            Property(
                name="section",
                data_type=DataType.TEXT,
            ),
            Property(
                name="image_path",
                data_type=DataType.TEXT,
            ),
        ],
    )
