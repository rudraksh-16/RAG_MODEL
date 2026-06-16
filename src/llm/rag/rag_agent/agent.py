from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from src.llm.logger import get_logger
from src.llm.rag.constant import RAGConstant
from src.llm.rag.rag_agent.prompt import SYSTEM_PROMPT
from src.llm.rag.rag_agent.tools.make_retrieval import get_retrieval

logger = get_logger("rag.agent")


def build_llm(
    provider: str = RAGConstant.PROVIDER,
    model: str = RAGConstant.MODEL,
    temperature: float = RAGConstant.TEMPERATURE,
):
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
        self.max_iteration = max_iteration
        llm = build_llm(provider=provider, model=model, temperature=temperature)
        self.agent = create_agent(
            llm,
            tools=[get_retrieval],
            system_prompt=SYSTEM_PROMPT,
        )

    def run(self, chat_history, user_message):
        if user_message == "":
            raise ValueError("Looks like no input was entered")
        chat_history.append({"role": "user", "content": user_message})
        result = self.agent.invoke(
            {"messages": chat_history},
            config={"recursion_limit": self.max_iteration * 2 + 1},
        )

        retrieval_calls = sum(
            1
            for m in result["messages"]
            for tc in getattr(m, "tool_calls", []) or []
            if tc.get("name") == "get_retrieval"
        )
        if retrieval_calls:
            logger.info(
                "ANSWER GROUNDED: %d retrieval call(s) to Weaviate before answering.",
                retrieval_calls,
            )
        else:
            logger.warning(
                "NO RETRIEVAL: answer produced WITHOUT querying the DB "
                "(came from LLM memory, not Weaviate)."
            )

        return result["messages"][-1].content
