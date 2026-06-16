from src.llm.rag.pipeline import rag_model


def main():
    print("Welcome to the Rag model. Type 'exit' to quit.\n")
    chat_history = []
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        answer = rag_model(chat_history, user_input)
        if answer is None:
            continue

        print(f"\nAssistant: {answer}\n")
        chat_history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
