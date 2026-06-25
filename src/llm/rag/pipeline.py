import warnings

from src.llm.logger import get_logger, log_duration
from src.llm.rag.rag_agent.agent import RagAgent

warnings.filterwarnings("ignore", category=ResourceWarning)

logger = get_logger("rag.pipeline")


def rag_model(chat_history: list, user_input: str):
    """Run one RAG turn, yielding the answer token-by-token as it streams.

    Yields nothing if the turn fails, so the interactive loop degrades gracefully
    instead of crashing.
    """
    logger.info("RAG TURN START | input=%r", user_input)
    agent = RagAgent()
    try:
        with log_duration(logger, "RAG TURN"):
            yield from agent.stream(chat_history=chat_history, user_message=user_input)
    except Exception as e:
        # Intentional deviation: one failed turn must not crash the interactive CLI
        # loop, so it is logged and the generator simply stops yielding.
        logger.error("RAG turn failed: %s", e)
