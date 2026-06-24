from src.backend.weaviate_I.client import close_client, get_client
from src.llm.rag.embeddings.model import get_embedding_model
from src.llm.rag.pipeline import rag_model


def main():
    print("Loading model...")
    get_embedding_model()
    get_client()
    print("Welcome to the Rag model. Type 'exit' to quit.\n")
    chat_history = []
    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                break

            print("\nAssistant: ", end="", flush=True)
            parts = []
            for token in rag_model(chat_history, user_input):
                print(token, end="", flush=True)
                parts.append(token)
            print("\n")

            answer = "".join(parts)
            if answer:
                chat_history.append({"role": "assistant", "content": answer})
    finally:
        close_client()


if __name__ == "__main__":
    main()
