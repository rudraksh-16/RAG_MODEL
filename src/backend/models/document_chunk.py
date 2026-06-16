from weaviate.classes.config import (
    Configure,
    Property,
    DataType,
    VectorDistances,
)


def initialize_document_chunk_collection(client) -> None:
    """
    DocumentChunk collection for RAG:
    - vectors provided manually
    - HNSW index enabled
    """

    if client.collections.exists("DocumentChunk"):
        return

    client.collections.create(
        name="DocumentChunk",
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
        ],
    )
