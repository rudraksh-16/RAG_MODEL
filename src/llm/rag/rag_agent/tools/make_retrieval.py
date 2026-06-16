import json

from langchain_core.tools import tool

from src.llm.logger import get_logger
from src.llm.rag.retrieval.search import Retriever
from src.llm.rag.retrieval.rerank import CohereReranker

logger = get_logger("rag.retrieval")


@tool
def get_retrieval(query: str) -> str:
    """Fetch the related document. Pass a refined, explicit version of the user's question."""
    retriever = Retriever()
    reranker = CohereReranker()
    try:
        logger.info("WEAVIATE QUERY: %r", query)
        docs = retriever.hybrid_search(query=query, alpha=0.5, limit=20)
        logger.info(
            "WEAVIATE HITS: %d chunks from DB | sources=%s",
            len(docs),
            [d["source"] for d in docs],
        )
        reranked = reranker.rerank(query=query, documents=docs, top_k=5)
        logger.info(
            "RERANKED top-%d (grounding sent to LLM): %s",
            len(reranked),
            [
                {
                    "source": d["source"],
                    "chunk_index": d["chunk_index"],
                    "rerank_score": round(d["rerank_score"], 4),
                }
                for d in reranked
            ],
        )
        return json.dumps(reranked)

    except Exception as e:
        logger.error("RETRIEVAL FAILED: %s", e)
        raise RuntimeError(f"Failed to load the chapter {e}")

    finally:
        reranker.close()
        retriever.close()
