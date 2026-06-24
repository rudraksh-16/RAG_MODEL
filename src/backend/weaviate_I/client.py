import weaviate
from weaviate.connect import ConnectionParams

from src.llm.config import RAGConfig

GRPC_PORT = 50051

_client = None


def get_client() -> weaviate.WeaviateClient:
    """Return the shared, connected Weaviate client, building it once on first use."""
    global _client
    if _client is None:
        client = weaviate.WeaviateClient(
            connection_params=ConnectionParams.from_url(
                RAGConfig.WEAVIATE_URL, grpc_port=GRPC_PORT
            )
        )
        client.connect()
        if not client.is_ready():
            raise RuntimeError("Weaviate is not ready")
        _client = client
    return _client


def close_client() -> None:
    """Close the shared Weaviate client and reset the singleton."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
