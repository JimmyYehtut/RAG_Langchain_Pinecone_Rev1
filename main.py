import asyncio
from app.ask import stream_answer

async def main():
    print("RAG Demo — LangChain 0.2 + Pinecone")
    print("Type 'exit' to quit.\n")

    while True:
        query = input("Your question: ").strip()
        if query.lower() in ["exit", "quit"]:
            break

        print("\nThinking...\n")
        async for chunk in stream_answer(query):
            print(chunk, end="", flush=True)
        print("\n" + "-" * 60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
