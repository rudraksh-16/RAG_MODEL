from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from src.llm.logger import get_logger, log_duration
from src.llm.rag.constant import RAGConstant
from src.llm.rag.rag_agent.prompt import SYSTEM_PROMPT
from src.llm.rag.rag_agent.tools.make_retrieval import get_retrieval

logger = get_logger("rag.agent")


def build_llm(
    provider: str = RAGConstant.PROVIDER,
    model: str = RAGConstant.MODEL,
    temperature: float = RAGConstant.TEMPERATURE,
) -> BaseChatModel:
    """Provider-agnostic chat model. Swap provider via RAGConstant.PROVIDER."""
    return init_chat_model(model, model_provider=provider, temperature=temperature)


class RagAgent:
    def __init__(
        self,
        provider: str = RAGConstant.PROVIDER,
        model: str = RAGConstant.MODEL,
        temperature: float = RAGConstant.TEMPERATURE,
        max_iteration: int = RAGConstant.DEFAULT_MAX_ITERATION,
    ):
        """Build the retrieval-augmented agent with its chat model and tools."""
        self.max_iteration = max_iteration
        llm = build_llm(provider=provider, model=model, temperature=temperature)
        self.agent = create_agent(
            llm,
            tools=[get_retrieval],
            system_prompt=SYSTEM_PROMPT,
        )

    def stream(self, chat_history, user_message):
        """Stream the answer token-by-token as the LLM generates it."""
        if user_message == "":
            raise ValueError("Looks like no input was entered")
        chat_history.append({"role": "user", "content": user_message})
        logger.info("AGENT INVOKED | model=%s | message=%r", RAGConstant.MODEL, user_message)

        used_retrieval = False
        streamed_chars = 0
        with log_duration(logger, "AGENT TURN"):
            for chunk, _meta in self.agent.stream(
                {"messages": chat_history},
                config={"recursion_limit": self.max_iteration * 2 + 1},
                stream_mode="messages",
            ):
                if getattr(chunk, "tool_call_chunks", None):
                    used_retrieval = True
                if getattr(chunk, "type", "") == "tool":
                    continue  # skip raw retrieval payload; stream only the LLM answer
                text = chunk.content
                if isinstance(text, str) and text:
                    streamed_chars += len(text)
                    yield text

        logger.info("AGENT TURN COMPLETE | streamed_chars=%d", streamed_chars)
        if used_retrieval:
            logger.info("ANSWER GROUNDED: retrieval call(s) to Weaviate before answering.")
        else:
            logger.warning(
                "NO RETRIEVAL: answer produced WITHOUT querying the DB "
                "(came from LLM memory, not Weaviate)."
            )
