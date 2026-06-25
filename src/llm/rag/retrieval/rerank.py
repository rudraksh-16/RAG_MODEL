import cohere
from typing import List

from src.llm.config import RAGConfig
from src.llm.logger import get_logger, log_duration
from src.llm.rag.constant import RAGConstant

logger = get_logger("rag.rerank")

_client = None


def get_cohere_client() -> cohere.Client:
    """Lazily build the (reused) Cohere client once."""
    global _client
    if _client is None:
        _client = cohere.Client(api_key=RAGConfig.COHERE_API_KEY)
    return _client


class CohereReranker:
    def __init__(self, client: cohere.Client, model: str = RAGConstant.COHERE_RERANK_MODEL) -> None:
        self.client = client
        self.model = model

    def rerank(self, query: str, documents: List[dict], top_k: int = 5) -> List[dict]:
        """Rerank documents by relevance to the query and attach rerank scores.

        documents: List[{text, source, chunk_id, score}]
        """

        texts = [doc["text"] for doc in documents]

        with log_duration(logger, "COHERE RERANK"):
            response = self.client.rerank(
                model=self.model, query=query, documents=texts, top_n=top_k
            )

        reranked_docs = []
        for r in response.results:
            doc = documents[r.index]
            doc["rerank_score"] = float(r.relevance_score)
            reranked_docs.append(doc)

        return reranked_docs
