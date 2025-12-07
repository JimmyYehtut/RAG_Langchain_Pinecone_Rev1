from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from app.ask import ask_question, stream_answer

app = FastAPI(title="RAG Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    answer = ask_question(req.question)
    return ChatResponse(answer=answer)

@app.post("/stream")
async def chat_stream(req: ChatRequest):
    async def token_generator():
        async for chunk in stream_answer(req.question):
            yield chunk
    return StreamingResponse(token_generator(), media_type="text/plain; charset=utf-8")

@app.get("/health")
async def health():
    return {"status": "ok"}