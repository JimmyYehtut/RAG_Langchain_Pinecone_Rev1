# Backend API & LangChain RAG Development Specification

## Purpose

This document defines the backend implementation requirements for the Enterprise Knowledge Platform.

Target Stack:

- FastAPI
- LangChain
- OpenAI
- Pinecone
- PostgreSQL
- Open WebUI (frontend only)
- RAGAS

---

# System Responsibilities

## FastAPI

Acts as the system boundary.

Responsibilities:

- Authentication validation
- Authorization enforcement
- RBAC policy enforcement
- Chat API
- Ingestion API
- Admin API
- Audit logging
- Conversation persistence

FastAPI MUST be the enforcement point for all security decisions.

Pinecone must never determine access rights.

---

# Personas

## Business Users

- PLG Officer
- HMG Officer
- CRG Officer
- Legal Officer
- IAG Officer

## Administrative Users

- System Admin

---

# Access Model

Every user belongs to:

- Department
- Role

Example:

```json
{
  "user_id": "123",
  "department": "PLG",
  "role": "Officer"
}
```

Documents may be:

- Department specific
- Shared across departments

Example metadata:

```json
{
  "owner_department": "PLG",
  "allowed_departments": [
    "PLG",
    "LEGAL",
    "IAG"
  ],
  "classification": "Internal"
}
```

---

# API Specification

## POST /chat

### Input

```json
{
  "message": "user question"
}
```

### Processing

1. Validate JWT
2. Resolve user department
3. Resolve user role
4. Build Pinecone metadata filter
5. Execute retrieval
6. Assemble prompt
7. Call LLM
8. Store conversation
9. Store audit record
10. Return answer

---

## POST /admin/upload

Upload document.

Allowed:

- PDF
- DOCX
- TXT

Returns:

```json
{
  "document_id": "uuid"
}
```

---

## POST /admin/ingest

Triggers ingestion pipeline.

Input:

```json
{
  "document_id": "uuid"
}
```

---

## GET /documents

Returns document metadata.

---

## GET /history

Returns user conversation history.

---

# LangChain Pipeline

## Stage 1 — Query Processing

Input:

```text
User Question
```

Tasks:

- Query cleanup
- Query rewriting
- Intent detection

Output:

```text
Optimized Query
```

---

## Stage 2 — Retrieval

Input:

- Optimized Query
- User Department
- User Role

Build filter:

```python
filter = {
    "allowed_departments": {
        "$in": [user_department]
    }
}
```

Execute:

```python
pinecone.similarity_search(
    query,
    filter=filter
)
```

Output:

Top-K chunks

---

## Stage 3 — Context Assembly

Tasks:

- Remove duplicates
- Rank chunks
- Merge context

Output:

```text
Context Package
```

---

## Stage 4 — Prompt Construction

System Prompt:

- Use retrieved context only
- Cite sources
- Do not hallucinate

Template:

```text
Context:
{context}

Question:
{question}
```

---

## Stage 5 — LLM Interaction

Provider:

OpenAI

Initial model:

- GPT-4.1

Future:

- GPT-5
- Bedrock Claude

Output:

Draft answer

---

## Stage 6 — Response Generation

Tasks:

- Attach citations
- Format markdown
- Return answer

---

# Pinecone Design

## Namespace Strategy

Recommended:

```text
enterprise-kb
```

Avoid one namespace per department.

Use metadata filtering instead.

---

## Metadata Schema

```json
{
  "document_id": "uuid",
  "document_name": "policy.pdf",
  "owner_department": "PLG",
  "allowed_departments": [
    "PLG",
    "LEGAL"
  ],
  "classification": "Internal",
  "document_type": "Policy",
  "version": "1.0"
}
```

---

# PostgreSQL Design

## Tables

### users

- id
- email
- department
- role

### conversations

- id
- user_id
- timestamp

### messages

- id
- conversation_id
- role
- content

### documents

- id
- name
- version

### feedback

- id
- message_id
- rating
- comment

### audit_logs

- id
- user_id
- query
- response
- timestamp

---

# Ingestion Pipeline

## Step 1

Upload document

---

## Step 2

Extract text

Libraries:

- pypdf
- docx

---

## Step 3

Chunking

Recommended:

- RecursiveCharacterTextSplitter

Chunk size:

```text
1000
```

Overlap:

```text
200
```

---

## Step 4

Generate embeddings

Model:

text-embedding-3-small

---

## Step 5

Attach metadata

Required:

- Department
- Access List
- Document Type
- Version

---

## Step 6

Store in Pinecone

---

# RAGAS Evaluation

Metrics:

- Faithfulness
- Answer Relevancy
- Context Precision
- Context Recall

Dataset format:

```json
{
  "question": "...",
  "ground_truth": "...",
  "retrieved_chunks": [],
  "generated_answer": "..."
}
```

---

# Coding Agent Tasks

Priority 1

- FastAPI skeleton
- PostgreSQL models
- Pinecone integration
- OpenAI integration

Priority 2

- RBAC middleware
- Ingestion service
- Audit logging

Priority 3

- RAGAS evaluation pipeline
- Admin dashboard APIs

---

# Non-Functional Requirements

- All APIs async
- JWT authentication
- RBAC enforcement
- Metadata-filtered retrieval
- Source citations mandatory
- Audit logs mandatory
- No direct Pinecone access from UI
- No security decisions inside Pinecone
