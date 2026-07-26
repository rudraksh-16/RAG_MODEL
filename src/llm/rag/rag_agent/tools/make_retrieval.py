import json

from langchain_core.tools import tool

from src.backend.weaviate_I.client import get_client
from src.llm.logger import get_logger, log_duration
from src.llm.rag.constant import RAGConstant
from src.llm.rag.embeddings.model import get_embedding_model
from src.llm.rag.retrieval.rerank import CohereReranker, get_cohere_client
from src.llm.rag.retrieval.search import Retriever

logger = get_logger("rag.retrieval")

_retriever = None
_reranker = None
_last_sources: list[dict] = []


def reset_sources() -> None:
    """Clear captured grounding sources at the start of a turn."""
    _last_sources.clear()


def get_last_sources() -> list[dict]:
    """Return the grounding chunks captured during the current turn."""
    return _last_sources


def _get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(client=get_client(), embedder=get_embedding_model())
    return _retriever


def _get_reranker() -> CohereReranker:
    global _reranker
    if _reranker is None:
        _reranker = CohereReranker(client=get_cohere_client())
    return _reranker


@tool
def get_retrieval(query: str) -> str:
    """Fetch the related document. Pass a refined, explicit version of the user's question."""
    retriever = _get_retriever()
    reranker = _get_reranker()
    try:
        with log_duration(logger, "RETRIEVAL TOOL"):
            return _run_retrieval(retriever, reranker, query)
    except Exception as e:
        logger.error("RETRIEVAL FAILED: %s", e)
        raise RuntimeError(f"Failed to load the chapter {e}")


def _run_retrieval(retriever: Retriever, reranker: CohereReranker, query: str) -> str:
    logger.info("WEAVIATE QUERY: %r", query)
    docs = retriever.hybrid_search(
        query=query,
        alpha=RAGConstant.HYBRID_SEARCH_ALPHA,
        limit=RAGConstant.RETRIEVAL_CANDIDATES,
    )
    logger.info(
        "WEAVIATE HITS: %d chunks from DB | sources=%s",
        len(docs),
        [d["source"] for d in docs],
    )
    reranked = reranker.rerank(
        query=query, documents=docs, top_k=RAGConstant.RERANK_TOP_K
    )
    logger.info(
        "RERANKED top-%d (grounding sent to LLM): %s",
        len(reranked),
        [
            {
                "source_file": d.get("source_file"),
                "page": d.get("page_number"),
                "type": d.get("element_type"),
                "rerank_score": round(d["rerank_score"], 4),
                "content": d.get("text"),
            }
            for d in reranked
        ],
    )
    _last_sources.extend(
        {
            "source_file": d.get("source_file"),
            "page": d.get("page_number"),
            "type": d.get("element_type"),
            "score": round(d["rerank_score"], 4),
        }
        for d in reranked
    )
    return json.dumps(reranked)
