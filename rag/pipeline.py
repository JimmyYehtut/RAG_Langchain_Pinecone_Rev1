"""6-stage enterprise RAG pipeline with BM25 reranking."""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from rank_bm25 import BM25Okapi

load_dotenv()

_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
_EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "ragindex")
_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1")
# Pinecone returns this many candidates; BM25 reranks them and keeps _RERANK_TOP_N
_RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "15"))
_RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "5"))

_SYSTEM_PROMPT = (
    "You are an enterprise knowledge assistant. "
    "Answer ONLY using the provided context. "
    "Do not hallucinate or add information not present in the context."
)

_RAG_TEMPLATE = """\
Context:
{context}

Question:
{question}

Instructions:
- Answer based solely on the context above.
- Do NOT embed inline citations or brackets in the answer text.
- If the context does not contain enough information, say so clearly.
- After your answer, add exactly one line listing only the document titles you used:

Source: <document title>

If you used multiple documents, separate them with a comma: Source: Title A, Title B
List only documents you actually referenced. Do not include unused documents.
"""


@dataclass
class PipelineResult:
    answer: str
    citations: list[dict] = field(default_factory=list)
    rewritten_query: str = ""
    raw_chunks: list[Document] = field(default_factory=list)


def _get_vectorstore() -> PineconeVectorStore:
    embeddings = OpenAIEmbeddings(model=_EMBEDDING_MODEL, dimensions=_EMBEDDING_DIM)
    return PineconeVectorStore.from_existing_index(index_name=_INDEX_NAME, embedding=embeddings)


# ── Stage 1: Query Processing ─────────────────────────────────────────────────

def _stage1_process_query(query: str, llm: ChatOpenAI) -> str:
    """Clean, rewrite, and detect intent of the user query."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a query optimizer for an enterprise knowledge base. "
                "Rewrite the user query to be clear, specific, and optimised for semantic search. "
                "Remove filler words, fix typos, and make implicit intent explicit. "
                "Return ONLY the rewritten query — no explanation.",
            ),
            ("human", "{query}"),
        ]
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"query": query}).strip()


# ── Stage 2: Retrieval ────────────────────────────────────────────────────────

def _stage2_retrieve(query: str, department: str, vectorstore: PineconeVectorStore) -> list[Document]:
    """Filtered semantic search — fetches a larger candidate pool for BM25 reranking.

    The department RBAC filter is enforced inside Pinecone so no unauthorised
    chunks are ever surfaced, even before reranking.
    """
    metadata_filter = {"allowed_departments": {"$in": [department]}}
    return vectorstore.similarity_search(
        query,
        k=_RETRIEVAL_TOP_K,
        filter=metadata_filter,
        namespace="enterprise-kb",
    )


# ── Stage 3: BM25 Reranking ───────────────────────────────────────────────────

def _stage3_rerank(query: str, chunks: list[Document]) -> list[Document]:
    """Rerank the semantic-search candidates with BM25 (Okapi BM25).

    BM25 scores each chunk by exact keyword overlap with the query using
    term frequency and inverse document frequency, which complements the
    semantic similarity used in retrieval — especially useful for queries
    containing specific codes, names, or technical terms.
    """
    # Deduplicate before scoring
    seen: set[str] = set()
    unique: list[Document] = []
    for doc in chunks:
        fingerprint = doc.page_content[:200]
        if fingerprint not in seen:
            seen.add(fingerprint)
            unique.append(doc)

    # Tokenise — lowercase split is sufficient for BM25 keyword matching
    tokenized_corpus = [doc.page_content.lower().split() for doc in unique]
    query_tokens = query.lower().split()

    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(query_tokens)  # numpy array, one score per doc

    # Sort by BM25 score descending, keep top-N
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    top_indices = ranked_indices[:_RERANK_TOP_N]

    reranked: list[Document] = []
    for idx in top_indices:
        doc = unique[idx]
        doc.metadata["bm25_score"] = round(float(scores[idx]), 4)
        reranked.append(doc)

    return reranked


# ── Stage 4: Context Assembly ─────────────────────────────────────────────────

def _clean_title(filename: str) -> str:
    """Convert a filename to a readable title: strip extension, replace separators."""
    name = os.path.splitext(filename)[0]
    return name.replace("_", " ").replace("-", " ").strip()


def _stage4_assemble_context(chunks: list[Document]) -> str:
    """Merge reranked chunks into a single context string with source labels."""
    return "\n\n---\n\n".join(
        f"[{_clean_title(doc.metadata.get('document_name', 'Unknown'))}]\n{doc.page_content}"
        for doc in chunks
    )


# ── Stage 5: LLM Interaction ──────────────────────────────────────────────────

def _stage5_call_llm(context: str, question: str, llm: ChatOpenAI) -> str:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PROMPT),
            ("human", _RAG_TEMPLATE),
        ]
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"context": context, "question": question})


# ── Stage 6: Response Generation ──────────────────────────────────────────────

def _stage6_build_response(answer: str, chunks: list[Document]) -> tuple[str, list[dict]]:
    """Attach structured citations derived from the BM25-reranked chunks."""
    citations: list[dict] = []
    seen_keys: set[str] = set()
    for i, doc in enumerate(chunks):
        doc_id = doc.metadata.get("document_id", "")
        doc_name = doc.metadata.get("document_name", "Unknown")
        # deduplicate by document_id when present, otherwise by document_name
        dedup_key = doc_id if doc_id else doc_name
        if dedup_key and dedup_key not in seen_keys:
            seen_keys.add(dedup_key)
            citations.append(
                {
                    "document_name": _clean_title(doc_name),
                    "document_id": doc_id,
                    "chunk_index": i,
                    "bm25_score": doc.metadata.get("bm25_score"),
                }
            )

    return answer, citations


# ── Public entry point ────────────────────────────────────────────────────────

def run_pipeline(query: str, department: str) -> PipelineResult:
    """Run all 6 pipeline stages and return a structured result."""
    llm = ChatOpenAI(model=_CHAT_MODEL, temperature=0)
    vectorstore = _get_vectorstore()

    # Stage 1 — query rewriting
    rewritten = _stage1_process_query(query, llm)

    # Stage 2 — filtered semantic retrieval (large candidate pool)
    candidates = _stage2_retrieve(rewritten, department, vectorstore)
    if not candidates:
        return PipelineResult(
            answer="No relevant documents found for your query in the accessible knowledge base.",
            rewritten_query=rewritten,
        )

    # Stage 3 — BM25 reranking → top-N
    reranked_chunks = _stage3_rerank(rewritten, candidates)

    # Stage 4 — context assembly
    context = _stage4_assemble_context(reranked_chunks)

    # Stage 5 — LLM answer generation
    answer = _stage5_call_llm(context, rewritten, llm)

    # Stage 6 — citation attachment
    final_answer, citations = _stage6_build_response(answer, reranked_chunks)

    return PipelineResult(
        answer=final_answer,
        citations=citations,
        rewritten_query=rewritten,
        raw_chunks=reranked_chunks,
    )


async def run_pipeline_async(query: str, department: str) -> PipelineResult:
    """Async wrapper — runs the synchronous pipeline in a thread pool."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_pipeline, query, department)
