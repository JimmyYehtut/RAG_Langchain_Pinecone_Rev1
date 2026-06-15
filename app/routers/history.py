"""GET /history — returns the current user's conversation history."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.db_models import Conversation
from app.models import ConversationOut, MessageOut

router = APIRouter(tags=["history"])


@router.get("/history", response_model=list[ConversationOut])
async def get_history(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user["user_id"]
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.timestamp.desc())
    )
    conversations = result.scalars().all()

    return [
        ConversationOut(
            id=conv.id,
            timestamp=conv.timestamp,
            messages=[
                MessageOut(id=msg.id, role=msg.role, content=msg.content)
                for msg in conv.messages
            ],
        )
        for conv in conversations
    ]
