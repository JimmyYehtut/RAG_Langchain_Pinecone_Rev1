# Code Execution Flow - app/main.py

## Entry Point Overview

This document traces the complete execution order of `app/main.py` from server startup through request handling.

---

## 1. SERVER STARTUP (Module Load)

When uvicorn starts the application, Python executes the module top-to-bottom:

```
app/main.py imported by uvicorn
│
├─ Lines 1-4: Import statements executed
│  ├─ os, time, uuid, json imported
│  ├─ FastAPI, CORSMiddleware, StreamingResponse imported
│  ├─ Pydantic BaseModel imported
│  └─ app.ask functions imported (ask_question, stream_answer)
│
├─ Line 14: FastAPI() instantiated
│  └─ Creates app object ready to handle requests
│
├─ Lines 16-22: CORSMiddleware added to app
│  └─ Enables cross-origin requests for Open-WebUI
│
├─ Lines 24-25: Module constants defined
│  ├─ MODEL_ID = "gpt-4.1" (from .env)
│  └─ RAG_MODEL_ID = "rag-pinecone"
│
├─ Lines 28-30: Message class defined
│  └─ Pydantic model for individual chat messages
│
├─ Lines 33-38: ChatCompletionRequest class defined
│  └─ Pydantic model for validating incoming requests
│
├─ Lines 41-45: Function _extract_query() defined
│  └─ Extracts user query from message list
│
├─ Lines 48-57: Function _make_chunk() defined
│  └─ Formats streamed response chunks as SSE
│
├─ Lines 60-68: Function _stream_sse() defined
│  └─ Generator function (NOT CALLED YET)
│
├─ Lines 71-83: @app.get("/v1/models") decorator registers endpoint
│  ├─ list_models() function decorated
│  └─ Route mapping created in FastAPI app
│
├─ Lines 86-112: @app.post("/v1/chat/completions") decorator registers endpoint
│  ├─ chat_completions() function decorated
│  └─ Route mapping created in FastAPI app
│
└─ ✅ Server ready, listening on port 8000
```

---

## 2. REQUEST: GET /v1/models (Client discovers model list)

**Triggered by:** Open-WebUI startup or model selector refresh

```
HTTP GET http://localhost:8000/v1/models

├─ FastAPI router matches route [Line 71: @app.get("/v1/models")]
│
├─ list_models() function called [Line 72]
│  ├─ async def list_models(): → FUNCTION START
│  │
│  ├─ Lines 73-83: Build response JSON
│  │  ├─ "object": "list"
│  │  ├─ "data": [model dict]
│  │  │  ├─ "id": RAG_MODEL_ID ("rag-pinecone")
│  │  │  ├─ "object": "model"
│  │  │  ├─ "created": current Unix timestamp via time.time()
│  │  │  └─ "owned_by": "local"
│  │  │
│  │  └─ Dict constructed
│  │
│  └─ Return response dict → FUNCTION END
│
└─ FastAPI serializes to JSON and sends to client
   └─ Client receives: {"object":"list","data":[{"id":"rag-pinecone",...}]}
```

---

## 3. REQUEST: POST /v1/chat/completions (Stream=False)

**Triggered by:** User sends message in Open-WebUI with streaming disabled

```
HTTP POST http://localhost:8000/v1/chat/completions
Body: {
  "messages": [{"role": "user", "content": "What is RAG?"}],
  "stream": false
}

├─ FastAPI validates request body against ChatCompletionRequest model [Line 33]
│  └─ Pydantic parses JSON into ChatCompletionRequest object
│
├─ chat_completions(request) function called [Line 87]
│  └─ async def chat_completions(request: ChatCompletionRequest): → FUNCTION START
│
│  ├─ STEP 1: Extract Query [Line 88]
│  │  │
│  │  ├─ query = _extract_query(request.messages)
│  │  │  └─ _extract_query() function called [Line 41]
│  │  │     ├─ def _extract_query(messages: list[Message]) -> str: → SUB-FUNCTION START
│  │  │     │
│  │  │     ├─ Line 42: for msg in reversed(messages)
│  │  │     │  └─ Iterate backwards through message list
│  │  │     │
│  │  │     ├─ Line 43: if msg.role == "user"
│  │  │     │  └─ Check if message is from user
│  │  │     │
│  │  │     ├─ Line 44: return msg.content
│  │  │     │  └─ Extract and return: "What is RAG?"
│  │  │     │
│  │  │     └─ _extract_query() returns → SUB-FUNCTION END
│  │  │
│  │  └─ query = "What is RAG?"
│
│  ├─ STEP 2: Check Streaming Flag [Line 90]
│  │  ├─ if request.stream: check
│  │  └─ RESULT: FALSE → Skip to non-streaming path
│
│  ├─ STEP 3: Get RAG Answer (BLOCKING) [Line 97]
│  │  │
│  │  ├─ answer = ask_question(query)
│  │  │  └─ ask_question() from app/ask.py [Line 3]
│  │  │     ├─ def ask_question(query: str) -> str: → SUB-FUNCTION START
│  │  │     │
│  │  │     ├─ Line 7: chain = build_retrieval_chain()
│  │  │     │  └─ Calls rag/retrieval_chain.py [Line 11]
│  │  │     │     ├─ def build_retrieval_chain(): → SUB-SUB-FUNCTION START
│  │  │     │     │
│  │  │     │     ├─ Line 12: vectorstore = create_or_load_vectorstore()
│  │  │     │     │  └─ Loads from rag/vectorstore.py
│  │  │     │     │     └─ Initializes Pinecone connection + OpenAI embeddings
│  │  │     │     │
│  │  │     │     ├─ Line 13: retriever = vectorstore.as_retriever(...)
│  │  │     │     │  └─ Creates LangChain retriever for vector search
│  │  │     │     │
│  │  │     │     ├─ Lines 15-19: ChatOpenAI LLM initialized
│  │  │     │     │  ├─ model="gpt-4.1" (from .env)
│  │  │     │     │  ├─ temperature=0
│  │  │     │     │  └─ streaming=True
│  │  │     │     │
│  │  │     │     ├─ Lines 22-24: ChatPromptTemplate created
│  │  │     │     │  └─ "Answer the question based only on..."
│  │  │     │     │
│  │  │     │     ├─ Lines 27-28: format_docs() function defined
│  │  │     │     │
│  │  │     │     ├─ Lines 30-38: RAG chain built using LCEL
│  │  │     │     │  ├─ "context": retriever | format_docs
│  │  │     │     │  ├─ "question": RunnablePassthrough()
│  │  │     │     │  ├─ | prompt
│  │  │     │     │  ├─ | llm
│  │  │     │     │  └─ | StrOutputParser()
│  │  │     │     │
│  │  │     │     ├─ Line 40: return rag_chain
│  │  │     │     └─ build_retrieval_chain() returns → SUB-SUB-FUNCTION END
│  │  │     │
│  │  │     ├─ Line 8: answer = chain.invoke(query)
│  │  │     │  └─ ⚠️ ACTUAL RAG PROCESSING HAPPENS HERE
│  │  │     │     ├─ Query "What is RAG?" converted to embedding
│  │  │     │     ├─ Pinecone searches for similar vectors
│  │  │     │     ├─ Top 4 documents retrieved (k=4 from Line 13)
│  │  │     │     ├─ Documents formatted as context
│  │  │     │     ├─ Prompt created: "Answer based on context...\n\n{context}\n\nQuestion: What is RAG?"
│  │  │     │     ├─ OpenAI GPT-4 LLM generates response
│  │  │     │     └─ Returns complete answer string
│  │  │     │
│  │  │     ├─ Line 9: return answer
│  │  │     └─ ask_question() returns answer string → SUB-FUNCTION END
│  │  │
│  │  └─ answer = "RAG (Retrieval-Augmented Generation) is..." (full string)
│
│  ├─ STEP 4: Generate Response ID [Line 98]
│  │  ├─ completion_id = f"chatcmpl-{uuid.uuid4().hex}"
│  │  └─ Example: "chatcmpl-a1b2c3d4e5f6..."
│
│  ├─ STEP 5: Build Response JSON [Lines 99-112]
│  │  ├─ Line 100: "id": completion_id
│  │  ├─ Line 101: "object": "chat.completion"
│  │  ├─ Line 102: "created": int(time.time())
│  │  ├─ Line 103: "model": RAG_MODEL_ID ("rag-pinecone")
│  │  ├─ Lines 104-109: "choices": [
│  │  │  ├─ "index": 0
│  │  │  ├─ "message": {
│  │  │  │  ├─ "role": "assistant"
│  │  │  │  └─ "content": answer (from STEP 3)
│  │  │  │ }
│  │  │  └─ "finish_reason": "stop"
│  │  │ ]
│  │  └─ Line 111: "usage": { token counts = 0 }
│  │
│  └─ Return response dict → FUNCTION END
│
└─ FastAPI serializes response JSON and sends to client
   
CLIENT RECEIVES:
{
  "id": "chatcmpl-a1b2c3d4e5f6...",
  "object": "chat.completion",
  "created": 1717862400,
  "model": "rag-pinecone",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "RAG (Retrieval-Augmented Generation) is..."
    },
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
}
```

---

## 4. REQUEST: POST /v1/chat/completions (Stream=True)

**Triggered by:** User sends message in Open-WebUI with streaming enabled

```
HTTP POST http://localhost:8000/v1/chat/completions
Body: {
  "messages": [{"role": "user", "content": "Explain embeddings"}],
  "stream": true
}

├─ FastAPI validates request body against ChatCompletionRequest model [Line 33]
│
├─ chat_completions(request) function called [Line 87]
│  └─ async def chat_completions(request: ChatCompletionRequest): → FUNCTION START
│
│  ├─ STEP 1: Extract Query [Line 88]
│  │  ├─ query = _extract_query(request.messages)
│  │  │  └─ [SAME AS REQUEST #3] → returns "Explain embeddings"
│  │  │
│  │  └─ query = "Explain embeddings"
│
│  ├─ STEP 2: Check Streaming Flag [Line 90]
│  │  ├─ if request.stream: check
│  │  └─ RESULT: TRUE → Continue to streaming path
│
│  ├─ STEP 3: Create StreamingResponse [Lines 91-95]
│  │  │
│  │  ├─ _stream_sse(query) called
│  │  │  └─ ⚠️ GENERATOR CREATED BUT NOT EXECUTED YET
│  │  │     └─ async def _stream_sse(query: str) -> AsyncIterator[str]: [Line 60]
│  │  │        └─ [Code at Lines 61-68 NOT YET RUNNING]
│  │  │
│  │  ├─ StreamingResponse(_stream_sse(query), ...) created [Line 91]
│  │  │  ├─ media_type="text/event-stream"
│  │  │  ├─ headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
│  │  │  └─ StreamingResponse object created (ready to stream)
│  │  │
│  │  └─ return StreamingResponse(...) → FUNCTION END [Line 95]
│
├─ FastAPI sends HTTP 200 response headers to client
│  ├─ Content-Type: text/event-stream
│  └─ Cache-Control: no-cache
│
└─ ✅ Client receives headers, starts listening for SSE events
   
   IMPORTANT: Generator execution begins NOW

   ├─ _stream_sse() generator execution starts [Line 60]
   │  └─ async def _stream_sse(query: str) -> AsyncIterator[str]: → SUB-FUNCTION START
   │
   │  ├─ STREAM STEP 1: Generate Completion ID [Line 61]
   │  │  └─ completion_id = f"chatcmpl-{uuid.uuid4().hex}"
   │  │     └─ Example: "chatcmpl-x1y2z3a4b5c6..."
   │
   │  ├─ STREAM STEP 2: Send Initial Chunk (Role) [Line 63]
   │  │  │
   │  │  ├─ yield _make_chunk("", completion_id)
   │  │  │  └─ _make_chunk() function called [Line 48]
   │  │  │     ├─ def _make_chunk(content: str, completion_id: str, ...) → SUB-SUB-FUNCTION START
   │  │  │     │
   │  │  │     ├─ Line 49: delta = {"content": ""} if "" else {} 
   │  │  │     │  └─ Empty content → delta = {}
   │  │  │     │
   │  │  │     ├─ Lines 50-56: Build chunk dict
   │  │  │     │  ├─ "id": completion_id
   │  │  │     │  ├─ "object": "chat.completion.chunk"
   │  │  │     │  ├─ "created": int(time.time())
   │  │  │     │  ├─ "model": "rag-pinecone"
   │  │  │     │  ├─ "choices": [{
   │  │  │     │  │  ├─ "index": 0
   │  │  │     │  │  ├─ "delta": {}
   │  │  │     │  │  └─ "finish_reason": None
   │  │  │     │  │ }]
   │  │  │     │  │
   │  │  │     │  └─ chunk dict = {...}
   │  │  │     │
   │  │  │     ├─ Line 57: return f"data: {json.dumps(chunk)}\n\n"
   │  │  │     │  └─ Formats as SSE: 
   │  │  │     │     "data: {"id":"chatcmpl-...","object":"chat.completion.chunk",...}\n\n"
   │  │  │     │
   │  │  │     └─ _make_chunk() returns → SUB-SUB-FUNCTION END
   │  │  │
   │  │  ├─ yield "data: {...}\n\n"
   │  │  │  └─ ✅ FIRST CHUNK SENT TO CLIENT over SSE stream
   │  │  │     └─ Client receives: data: {"object":"chat.completion.chunk",...}
   │  │  │
   │  │  └─ Control returns to _stream_sse() after client receives
   │
   │  ├─ STREAM STEP 3: Iterate Through RAG Streamed Answer [Line 64]
   │  │  │
   │  │  ├─ async for chunk in stream_answer(query)
   │  │  │  └─ stream_answer() from app/ask.py [Line 11]
   │  │  │     ├─ async def stream_answer(query: str): → SUB-FUNCTION START
   │  │  │     │
   │  │  │     ├─ Line 16: chain = build_retrieval_chain()
   │  │  │     │  └─ [SAME AS REQUEST #3] → Returns RAG chain
   │  │  │     │
   │  │  │     ├─ Line 17: async for chunk in chain.astream(query)
   │  │  │     │  └─ ⚠️ ACTUAL STREAMING RAG PROCESSING HAPPENS HERE
   │  │  │     │     ├─ Query "Explain embeddings" converted to embedding
   │  │  │     │     ├─ Pinecone searches for similar vectors (async)
   │  │  │     │     ├─ Top 4 documents retrieved
   │  │  │     │     ├─ Documents formatted as context
   │  │  │     │     ├─ Prompt created
   │  │  │     │     ├─ OpenAI LLM STREAMS tokens ONE-BY-ONE
   │  │  │     │     │  ├─ "Embeddings"
   │  │  │     │     │  ├─ " are"
   │  │  │     │     │  ├─ " vectors"
   │  │  │     │     │  ├─ " that"
   │  │  │     │     │  ├─ " represent"
   │  │  │     │     │  └─ ...
   │  │  │     │     └─ Each token yielded immediately
   │  │  │     │
   │  │  │     ├─ Line 18: yield chunk
   │  │  │     │  └─ Each token yielded from stream_answer()
   │  │  │     │
   │  │  │     └─ stream_answer() yields tokens one-by-one → SUB-FUNCTION YIELDS
   │  │  │
   │  │  ├─ chunk = first token = "Embeddings"
   │  │  ├─ chunk = second token = " are"
   │  │  ├─ chunk = third token = " vectors"
   │  │  ├─ ... [loop continues]
   │  │  └─ [LOOP REPEATS for each token from LLM]
   │
   │  ├─ STREAM STEP 4: Process Each Token [Lines 65-66]
   │  │  │
   │  │  ├─ Line 65: if chunk (skip empty chunks)
   │  │  │  └─ True for all non-empty tokens
   │  │  │
   │  │  ├─ Line 66: yield _make_chunk(chunk, completion_id)
   │  │  │  └─ _make_chunk() function called [Line 48]
   │  │  │     ├─ def _make_chunk(content: str, ...) [content="Embeddings"] → SUB-SUB-FUNCTION START
   │  │  │     │
   │  │  │     ├─ Line 49: delta = {"content": "Embeddings"} if "Embeddings" else {}
   │  │  │     │  └─ delta = {"content": "Embeddings"}
   │  │  │     │
   │  │  │     ├─ Lines 50-56: Build chunk dict
   │  │  │     │  ├─ "id": completion_id
   │  │  │     │  ├─ "object": "chat.completion.chunk"
   │  │  │     │  ├─ "created": int(time.time())
   │  │  │     │  ├─ "model": "rag-pinecone"
   │  │  │     │  ├─ "choices": [{
   │  │  │     │  │  ├─ "index": 0
   │  │  │     │  │  ├─ "delta": {"content": "Embeddings"}
   │  │  │     │  │  └─ "finish_reason": None
   │  │  │     │  │ }]
   │  │  │     │  │
   │  │  │     │  └─ chunk dict = {...}
   │  │  │     │
   │  │  │     ├─ Line 57: return f"data: {json.dumps(chunk)}\n\n"
   │  │  │     │
   │  │  │     └─ _make_chunk() returns → SUB-SUB-FUNCTION END
   │  │  │
   │  │  ├─ yield "data: {"object":"chat.completion.chunk","choices":[{"delta":{"content":"Embeddings"}}]}\n\n"
   │  │  │  └─ ✅ TOKEN CHUNK SENT TO CLIENT over SSE stream
   │  │  │     └─ Client receives token: "Embeddings"
   │  │  │
   │  │  └─ [LOOP CONTINUES - repeat for each token from LLM]
   │  │     └─ Client sees REAL-TIME typing effect
   │
   │  ├─ STREAM STEP 5: Send Final Empty Chunk with finish_reason [Line 67]
   │  │  │
   │  │  ├─ yield _make_chunk("", completion_id, finish_reason="stop")
   │  │  │  └─ _make_chunk() function called [Line 48]
   │  │  │     ├─ def _make_chunk(content: str, ..., finish_reason="stop") → SUB-SUB-FUNCTION START
   │  │  │     │
   │  │  │     ├─ Line 49: delta = {} (empty)
   │  │  │     │
   │  │  │     ├─ Lines 50-56: Build final chunk dict
   │  │  │     │  ├─ "choices": [{
   │  │  │     │  │  ├─ "delta": {}
   │  │  │     │  │  └─ "finish_reason": "stop"
   │  │  │     │  │ }]
   │  │  │     │  │
   │  │  │     │  └─ chunk dict = {...}
   │  │  │     │
   │  │  │     ├─ Line 57: return f"data: {...}\n\n"
   │  │  │     │
   │  │  │     └─ _make_chunk() returns → SUB-SUB-FUNCTION END
   │  │  │
   │  │  ├─ yield "data: {...,\"finish_reason\":\"stop\"}\n\n"
   │  │  │  └─ ✅ FINAL CHUNK SENT TO CLIENT
   │  │  │     └─ Client understands response is complete
   │  │  │
   │  │  └─ Control returns to _stream_sse()
   │
   │  ├─ STREAM STEP 6: Send Terminator [Line 68]
   │  │  ├─ yield "data: [DONE]\n\n"
   │  │  │  └─ ✅ TERMINATOR SENT TO CLIENT
   │  │  │     └─ SSE stream officially ends
   │  │  │
   │  │  └─ Control returns to _stream_sse()
   │
   │  └─ _stream_sse() generator ends → SUB-FUNCTION ENDS

└─ ✅ Streaming response complete - connection closed
   
CLIENT RECEIVES (over time):
data: {"object":"chat.completion.chunk","choices":[{"delta":{},"finish_reason":null}]}

data: {"object":"chat.completion.chunk","choices":[{"delta":{"content":"Embeddings"},"finish_reason":null}]}

data: {"object":"chat.completion.chunk","choices":[{"delta":{"content":" are"},"finish_reason":null}]}

data: {"object":"chat.completion.chunk","choices":[{"delta":{"content":" vectors"},"finish_reason":null}]}

... [more tokens] ...

data: {"object":"chat.completion.chunk","choices":[{"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

---

## Summary: Function Call Hierarchy

### Non-Streaming Path:
```
chat_completions(request)
  ├─ _extract_query(messages)
  │  └─ returns: query string
  │
  └─ ask_question(query)
     └─ build_retrieval_chain()
        └─ chain.invoke(query)
           └─ returns: full answer string
```

### Streaming Path:
```
chat_completions(request)
  ├─ _extract_query(messages)
  │  └─ returns: query string
  │
  └─ StreamingResponse(_stream_sse(query))
     └─ _stream_sse(query) [ASYNC GENERATOR]
        ├─ yield _make_chunk("", completion_id)
        │  └─ Initial chunk
        │
        ├─ stream_answer(query)
        │  └─ build_retrieval_chain()
        │     └─ chain.astream(query)
        │        └─ yields: tokens one-by-one
        │
        ├─ for each token:
        │  └─ yield _make_chunk(token, completion_id)
        │
        ├─ yield _make_chunk("", completion_id, finish_reason="stop")
        │  └─ Final chunk
        │
        └─ yield "data: [DONE]\n\n"
           └─ Terminator
```

---

## Key Points

1. **Server Startup**: All routes and middleware registered before first request arrives
2. **Non-Streaming**: `ask_question()` blocks until full answer received, then returns complete response
3. **Streaming**: Generator yields chunks as they arrive, client sees real-time typing
4. **RAG Processing**: Happens inside `chain.invoke()` or `chain.astream()` - Pinecone retrieval + OpenAI LLM
5. **SSE Format**: All chunks wrapped as `data: {json}\n\n` for Server-Sent Events protocol
6. **Terminator**: `[DONE]` signals end of stream (OpenAI protocol requirement)
