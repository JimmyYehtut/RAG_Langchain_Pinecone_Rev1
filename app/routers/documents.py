"""GET /documents — returns document metadata visible to the current user's department."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.db_models import Document
from app.models import DocumentOut

router = APIRouter(tags=["documents"])


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    department = current_user["department"]
    result = await db.execute(select(Document))
    docs = result.scalars().all()

    visible = []
    for doc in docs:
        allowed: list[str] = json.loads(doc.allowed_departments)
        if department in allowed or current_user.get("role") == "Admin":
            visible.append(
                DocumentOut(
                    id=doc.id,
                    name=doc.name,
                    owner_department=doc.owner_department,
                    allowed_departments=allowed,
                    classification=doc.classification,
                    document_type=doc.document_type,
                    version=doc.version,
                    status=doc.status,
                )
            )

    return visible
