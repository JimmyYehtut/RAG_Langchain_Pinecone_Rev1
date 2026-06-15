import os
import time
import uuid
import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

# Use the Windows native certificate store for all outbound TLS connections.
# Required on Windows where the Python bundled CA bundle doesn't include corporate/OS certs.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.ask import ask_question, stream_answer
from app.database import create_tables
from app import auth as auth_module
from app.routers import chat, admin, documents, history

MODEL_ID = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1")
RAG_MODEL_ID = "ai-knowledge"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(title="Enterprise Knowledge Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Enterprise routes ──────────────────────────────────────────────────────────
app.include_router(auth_module.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(documents.router)
app.include_router(history.router)


# ── Open WebUI-compatible endpoints (kept for backward compatibility) ──────────

class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = RAG_MODEL_ID
    messages: list[Message]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None


def _extract_query(messages: list[Message]) -> str:
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content
    raise HTTPException(status_code=400, detail="No user message found")


def _make_chunk(content: str, completion_id: str, finish_reason: str | None = None) -> str:
    delta = {"content": content} if content else {}
    chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": RAG_MODEL_ID,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }
    return f"data: {json.dumps(chunk)}\n\n"


async def _stream_sse(query: str) -> AsyncIterator[str]:
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    yield _make_chunk("", completion_id)
    async for chunk in stream_answer(query):
        if chunk:
            yield _make_chunk(chunk, completion_id)
    yield _make_chunk("", completion_id, finish_reason="stop")
    yield "data: [DONE]\n\n"


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": RAG_MODEL_ID,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    query = _extract_query(request.messages)

    if request.stream:
        return StreamingResponse(
            _stream_sse(query),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    answer = ask_question(query)
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": RAG_MODEL_ID,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
