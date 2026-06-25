from src.llm.rag.pipeline import rag_model
import warnings

warnings.filterwarnings("ignore", category=ResourceWarning)


def main():
    """
    Entry point for running the RAG Agent
    """
    chat_history = []

    print("RAG Agent is running. Type 'exit' to quit.\n")

    while True:
        user_input = input("[You]: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            print("\n Exiting RAG Agent.")
            break

        try:
            response,_ = rag_model(chat_history=chat_history,user_input=user_input)
            # print(tool_output)
            # user_message = {"role": "user", "content": user_input}
            assistent = {"role": "assistant", "content": response}
            chat_history.append(assistent)
            
            print(f"\n[Agent]: {response}\n")
            # print(chat_history)

        except Exception as e:
            print(f"\n Error: {e}\n")


if __name__ == "__main__":
    main()
