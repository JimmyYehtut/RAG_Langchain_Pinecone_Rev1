from rag.retrieval_chain import build_retrieval_chain

def ask_question(query: str) -> str:
    """
    Ask a question to the RAG system and return the answer.
    """
    chain = build_retrieval_chain()
    answer = chain.invoke(query)
    return answer

async def stream_answer(query: str):
    """
    Stream the answer from the RAG system chunk by chunk (async).
    Requires the underlying LLM to be created with streaming=True.
    """
    chain = build_retrieval_chain()
    async for chunk in chain.astream(query):
        yield chunk
