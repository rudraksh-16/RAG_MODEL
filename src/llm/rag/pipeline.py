import warnings

from src.llm.rag.rag_agent.agent import RagAgent

warnings.filterwarnings("ignore", category=ResourceWarning)


def rag_model(chat_history, user_input):
    agent = RagAgent()
    try:
        return agent.run(chat_history=chat_history, user_message=user_input)

    except Exception as e:
        print(f"\n Error: {e}\n")
