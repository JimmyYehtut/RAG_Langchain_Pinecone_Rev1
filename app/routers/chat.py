"""POST /chat — 10-step processing per spec."""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.db_models import AuditLog, Conversation, Message
from app.models import ChatRequest, ChatResponse, Citation
from rag.pipeline import run_pipeline_async

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    # Step 1: JWT already validated by get_current_user dependency
    # Step 2: Resolve user department
    department = current_user["department"]
    # Step 3: Resolve user role (available in current_user["role"])
    user_id = current_user["user_id"]

    # Step 4+5: Build Pinecone filter + execute retrieval (inside pipeline)
    # Step 6+7: Assemble prompt + call LLM (inside pipeline)
    result = await run_pipeline_async(body.message, department)

    # Step 8: Store conversation + messages
    conversation = Conversation(user_id=user_id, timestamp=datetime.utcnow())
    db.add(conversation)
    await db.flush()  # populate conversation.id

    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=body.message,
    )
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result.answer,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.flush()

    # Step 9: Store audit record
    audit = AuditLog(
        user_id=user_id,
        query=body.message,
        response=result.answer,
        timestamp=datetime.utcnow(),
    )
    db.add(audit)
    await db.commit()

    # Step 10: Return answer
    citations = [
        Citation(
            document_name=c["document_name"],
            document_id=c["document_id"],
            chunk_index=c["chunk_index"],
        )
        for c in result.citations
    ]

    return ChatResponse(
        answer=result.answer,
        citations=citations,
        conversation_id=conversation.id,
        message_id=assistant_msg.id,
    )
