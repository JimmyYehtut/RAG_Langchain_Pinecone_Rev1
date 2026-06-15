import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from .vectorstore import create_or_load_vectorstore

load_dotenv()

def build_retrieval_chain():
    vectorstore = create_or_load_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        temperature=0,
        streaming=True,
    )

    # Create a prompt template
    prompt = ChatPromptTemplate.from_template(
        "Answer the question based only on the following context. "
        "At the end of your answer, list the document titles you used as sources under a 'Sources:' heading.\n\n"
        "{context}\n\n"
        "Question: {question}"
    )

    # Build RAG chain using LCEL (LangChain Expression Language)
    def format_docs(docs):
        parts = []
        for doc in docs:
            title = doc.metadata.get("title") or doc.metadata.get("source", "Unknown")
            parts.append(f"[Title: {title}]\n{doc.page_content}")
        return "\n\n".join(parts)

    rag_chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain
