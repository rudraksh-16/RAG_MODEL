from sentence_transformers import SentenceTransformer
from src.llm.config import RAGConfig

# Intentional build-once singleton: the embedding model is reused across all calls.
_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    """Return the shared SentenceTransformer embedding model, building it once."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(RAGConfig.EMBEDDING_MODEL_NAME)
    return _embedding_model
