import cohere
from typing import List
from sentence_transformers import CrossEncoder
import torch 

from src.llm.config import RAGConfig
from src.llm.rag.constant import RAGConstant


class CohereReranker:
    def __init__(self, model: str = RAGConstant.COHERE_RERANK_MODEL):
        self.client = cohere.Client(api_key=RAGConfig.COHERE_API_KEY)
        self.model = model

    def rerank(self, query: str, documents: List[dict], top_k: int = 5) -> List[dict]:
        """
        documents: List[{text, source, chunk_id, score}]
        """

        texts = [doc["text"] for doc in documents]

        response = self.client.rerank(
            model=self.model, query=query, documents=texts, top_n=top_k
        )

        reranked_docs = []
        for r in response.results:
            doc = documents[r.index]
            doc["rerank_score"] = float(r.relevance_score)
            reranked_docs.append(doc)

        return reranked_docs

    def close(self):
        if hasattr(self.client, "close"):
            self.client.close()


class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name,activation_fn=torch.nn.Sigmoid())

    def rerank(self, query: str, documents: List[dict], top_k: int = 5) -> List[dict]:
        """
        documents: List[{text, source, chunk_index, score}]
        """

        pairs = [(query, doc["text"]) for doc in documents]

        scores = self.model.predict(pairs)

        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)

        documents.sort(key=lambda x: x["rerank_score"], reverse=True)

        return documents[:top_k]
