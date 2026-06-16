from sentence_transformers import SentenceTransformer
from src.llm.config import RAGConfig

_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(RAGConfig.EMBEDDING_MODEL_NAME)
    return _embedding_model
