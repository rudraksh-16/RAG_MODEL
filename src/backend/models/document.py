import logging
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
from src.backend.config import Config

logger = logging.getLogger(__name__)


def initialize_document_collection(client) -> None:
    """
    Create the Document collection in Weaviate if it does not already exist.
    Official Weaviate v4 configuration.
    """
    if client.collections.exists(Config.DOCUMENT_COLLECTION):
        logger.info(
            "Collection '%s' already exists. Skipping creation.",
            Config.DOCUMENT_COLLECTION,
        )
        return

    logger.info(
        "Creating collection '%s'...",
        Config.DOCUMENT_COLLECTION,
    )

    client.collections.create(
        name=Config.DOCUMENT_COLLECTION,
        vectorizer_config=Configure.Vectorizer.none(),
        vector_index_config=Configure.VectorIndex.hnsw(
            distance_metric=VectorDistances.COSINE,
            ef_construction=128,
            max_connections=32,
        ),
        properties=[
            Property(
                name="document_path",
                data_type=DataType.TEXT,
            ),
            Property(
                name="metadata",
                data_type=DataType.TEXT,
            ),
            Property(
                name="created_at",
                data_type=DataType.DATE,
            ),
            Property(
                name="updated_at",
                data_type=DataType.DATE,
            ),
            Property(
                name="deleted_at",
                data_type=DataType.DATE,
            ),
        ],
    )

    logger.info(
        "Collection '%s' created successfully.",
        Config.DOCUMENT_COLLECTION,
    )
