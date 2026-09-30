# RAG LangChain + Pinecone (Enterprise RAG Portfolio Project)

An enterprise-focused Retrieval-Augmented Generation (RAG) platform built with FastAPI, LangChain, OpenAI, and Pinecone.

## Project Summary

This project demonstrates a production-style RAG backend with:
- Role-based and department-based document access
- Document upload + ingestion pipeline
- Hybrid retrieval (semantic search + BM25 reranking)
- Chat endpoint with citations, audit logging, and history tracking
- Open WebUI-compatible chat-completion endpoints

## Key Features

- **Secure API boundary with FastAPI**
  - JWT authentication
  - RBAC enforcement for admin and user flows
- **Enterprise document lifecycle**
  - Upload support for PDF, DOCX, TXT
  - Metadata-aware ingestion into Pinecone
- **Hybrid retrieval quality**
  - Vector retrieval + BM25 reranking
  - Configurable retrieval and reranking limits
- **Operational tracking**
  - Conversation persistence
  - Audit logging
  - User history retrieval

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy (async), Uvicorn
- **RAG Orchestration:** LangChain
- **LLMs/Embeddings:** OpenAI
- **Vector Database:** Pinecone
- **Reranking:** rank-bm25
- **Evaluation:** RAGAS

## Repository Structure

```text
app/        FastAPI app, auth, RBAC, routers, models, DB integration
rag/        Retrieval pipeline, Pinecone/vectorstore integration
ingest/     Document ingestion workflow (load, chunk, embed, store)
frontend/   Frontend assets
docs/       Supporting design and implementation notes
eval/       Evaluation-related files
```

## Core API Endpoints

- `POST /chat` — RAG chat with citations and persistence
- `POST /admin/upload` — Upload document (admin)
- `POST /admin/ingest` — Ingest uploaded document (admin)
- `GET /documents` — List visible document metadata
- `GET /history` — Fetch user conversation history
- `GET /v1/models` — Open WebUI-compatible model listing
- `POST /v1/chat/completions` — Open WebUI-compatible chat endpoint

## Configuration (Environment Variables)

Common variables used in this project:
- `OPENAI_API_KEY`
- `OPENAI_CHAT_MODEL` (default: `gpt-4.1`)
- `OPENAI_EMBEDDING_MODEL` (default: `text-embedding-3-small`)
- `PINECONE_API_KEY`
- `PINECONE_INDEX_NAME`
- `PINECONE_CLOUD` (default: `aws`)
- `PINECONE_ENVIRONMENT` (default: `us-east-1`)
- `EMBEDDING_DIMENSION` (default: `1024`)
- `RETRIEVAL_TOP_K` (default: `15`)
- `RERANK_TOP_N` (default: `5`)
- `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`
- `UPLOADS_DIR` (default: `uploads`)

## Local Setup

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Optional demo CLI:

```bash
python main.py
```

## Portfolio Value

This repository showcases practical experience in:
- Building secure, API-first AI backends
- Implementing end-to-end RAG pipelines
- Combining semantic and lexical retrieval methods
- Designing systems for enterprise governance and traceability

## Supporting Documentation

- [Enterprise RAG Backend Spec](Enterprise_RAG_Backend_Spec.md)
- [Reranking Methodology](RERANKING_METHODOLOGY.md)
- [Execution Flow](EXECUTION_FLOW.md)
