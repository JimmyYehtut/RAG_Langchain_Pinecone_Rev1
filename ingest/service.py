"""Ingestion service — orchestrates the full 6-step pipeline for a single document."""
import asyncio
import os

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from ingest.load_documents import load_documents_from_paths
from ingest.chunk_documents import chunk_documents

_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
_EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "ragindex")
_NAMESPACE = "enterprise-kb"


def _attach_metadata(
    chunks: list[Document],
    document_id: str,
    document_name: str,
    owner_department: str,
    allowed_departments: list[str],
    classification: str,
    document_type: str,
    version: str,
) -> list[Document]:
    for chunk in chunks:
        chunk.metadata.update(
            {
                "document_id": document_id,
                "document_name": document_name,
                "owner_department": owner_department,
                "allowed_departments": allowed_departments,
                "classification": classification,
                "document_type": document_type,
                "version": version,
            }
        )
    return chunks


def _store_in_pinecone(chunks: list[Document]) -> int:
    embeddings = OpenAIEmbeddings(model=_EMBEDDING_MODEL, dimensions=_EMBEDDING_DIM)
    PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=_INDEX_NAME,
        namespace=_NAMESPACE,
    )
    return len(chunks)


def run_ingestion_pipeline_sync(
    file_path: str,
    document_id: str,
    document_name: str,
    owner_department: str,
    allowed_departments: list[str],
    classification: str = "Internal",
    document_type: str = "General",
    version: str = "1.0",
) -> int:
    """Steps 1-6: load → extract → chunk → embed → attach metadata → store. Returns chunk count."""
    # Steps 1+2: load and extract text
    docs = load_documents_from_paths([file_path])

    # Step 3: chunk
    chunks = chunk_documents(docs)

    # Step 5: attach metadata
    chunks = _attach_metadata(
        chunks,
        document_id=document_id,
        document_name=document_name,
        owner_department=owner_department,
        allowed_departments=allowed_departments,
        classification=classification,
        document_type=document_type,
        version=version,
    )

    # Step 6: store in Pinecone
    return _store_in_pinecone(chunks)


async def run_ingestion_pipeline(
    file_path: str,
    document_id: str,
    document_name: str,
    owner_department: str,
    allowed_departments: list[str],
    classification: str = "Internal",
    document_type: str = "General",
    version: str = "1.0",
) -> int:
    """Async wrapper — runs the blocking ingestion in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        run_ingestion_pipeline_sync,
        file_path,
        document_id,
        document_name,
        owner_department,
        allowed_departments,
        classification,
        document_type,
        version,
    )
