# RAG LangChain Pinecone Platform

An enterprise-focused Retrieval-Augmented Generation (RAG) platform built with **FastAPI**, **LangChain**, **Pinecone**, and **OpenAI**, with a **React + Vite** frontend.

## Project Snapshot

- **Project Type:** Enterprise Knowledge Assistant
- **Primary Goal:** Secure question-answering over internal documents with source-grounded responses
- **Core Capabilities:** Document ingestion, vector search, role-aware retrieval flow, chat API, and conversation history

## Key Features

- RAG pipeline powered by LangChain and Pinecone
- FastAPI backend with modular routers
- OpenAI-compatible chat completion endpoints (`/v1/chat/completions`)
- Document upload + ingestion workflow
- Conversation history and document listing endpoints
- Evaluation support using RAGAS

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, Uvicorn
- **LLM/RAG:** LangChain, OpenAI, Pinecone
- **Frontend:** React, TypeScript, Vite
- **Data & Processing:** PostgreSQL (async), pypdf, python-docx
- **Evaluation:** RAGAS

## API Surface (Current)

- `POST /chat`
- `GET /history`
- `GET /documents`
- `POST /upload`
- `POST /ingest`
- `GET /v1/models`
- `POST /v1/chat/completions`

## Repository Structure

```text
app/        FastAPI app, routers, auth, DB models
ingest/     Document loading, chunking, embedding, storage
rag/        Retrieval and vector store integration logic
api/        Server entrypoint wrapper
frontend/   React + TypeScript client
eval/       Evaluation scripts (RAGAS)
docs/       Sample source documents
```

## Quick Start

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run backend:

   ```bash
   uvicorn app.main:app --reload
   ```

3. (Optional) Start frontend:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Why This Project Belongs in a Portfolio

- Demonstrates practical RAG system design
- Covers backend API architecture and LLM integration
- Includes ingestion pipeline and evaluation workflow
- Shows full-stack capability with Python + TypeScript
