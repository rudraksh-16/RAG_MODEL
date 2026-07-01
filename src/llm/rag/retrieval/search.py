from typing import List

from src.backend.config import Config
from src.llm.logger import get_logger, log_duration
from src.llm.rag.constant import RAGConstant

logger = get_logger("rag.search")

SEARCH_PROPERTIES = [
    "chunk_text",
    "document_id",
    "chunk_index",
    "source_file",
    "page_number",
    "element_type",
    "section",
    "image_path",
]


def _base_fields(obj) -> dict:
    """Map a Weaviate object's shared properties into the result dict."""
    props = obj.properties
    return {
        "text": props["chunk_text"],
        "source": props["document_id"],
        "chunk_index": props["chunk_index"],
        "source_file": props.get("source_file"),
        "page_number": props.get("page_number"),
        "element_type": props.get("element_type"),
        "section": props.get("section"),
        "image_path": props.get("image_path"),
    }


class Retriever:
    def __init__(self, client, embedder) -> None:
        self.client = client
        self.collection = client.collections.get(Config.CHUNK_COLLECTION)
        self.embedder = embedder

    def _encode(self, text: str) -> list:
        with log_duration(logger, "EMBED ENCODE"):
            return self.embedder.encode([text], normalize_embeddings=True)[0].tolist()

    def vector_search(self, query: str, limit: int = RAGConstant.RERANK_TOP_K) -> List[dict]:
        """Pure vector (semantic) search."""
        response = self.collection.query.near_vector(
            near_vector=self._encode(query),
            limit=limit,
            return_properties=SEARCH_PROPERTIES,
        )
        return [
            {**_base_fields(obj), "distance": obj.metadata.distance}
            for obj in response.objects
        ]

    def hybrid_search(
        self,
        query: str,
        alpha: float = RAGConstant.HYBRID_SEARCH_ALPHA,
        limit: int = RAGConstant.RETRIEVAL_CANDIDATES,
        vector_text: str | None = None,
    ) -> List[dict]:
        """Hybrid search: vector + BM25."""
        vector = self._encode(vector_text or query)
        with log_duration(logger, "WEAVIATE HYBRID QUERY"):
            response = self.collection.query.hybrid(
                query=query,
                vector=vector,
                alpha=alpha,
                limit=limit,
                return_properties=SEARCH_PROPERTIES,
            )
        return [
            {
                **_base_fields(obj),
                "score": (
                    obj.metadata.score
                    if obj.metadata.score is not None
                    else obj.metadata.distance
                ),
            }
            for obj in response.objects
        ]
