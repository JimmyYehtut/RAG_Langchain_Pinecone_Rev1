import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from .pinecone_init import get_pinecone_index

load_dotenv()

EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "ragindex")

def get_embeddings():
    """
    Return an OpenAIEmbeddings instance configured from environment.
    For text-embedding-3-small and text-embedding-3-large, we can specify custom dimensions.
    """
    if EMBEDDING_MODEL in ["text-embedding-3-small", "text-embedding-3-large"]:
        return OpenAIEmbeddings(model=EMBEDDING_MODEL, dimensions=EMBEDDING_DIMENSION)
    else:
        return OpenAIEmbeddings(model=EMBEDDING_MODEL)


def create_or_load_vectorstore(documents=None):
    embeddings = get_embeddings()
    
    # Ensure the index exists with the correct dimension
    get_pinecone_index(dimension=EMBEDDING_DIMENSION)

    if documents:
        return PineconeVectorStore.from_documents(
            documents=documents,
            embedding=embeddings,
            index_name=PINECONE_INDEX_NAME
        )

    return PineconeVectorStore.from_existing_index(
        index_name=PINECONE_INDEX_NAME,
        embedding=embeddings
    )
