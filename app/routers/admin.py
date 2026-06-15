"""POST /admin/upload and POST /admin/ingest — admin-only endpoints."""
import json
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.db_models import Document
from app.models import IngestRequest, IngestResponse, UploadResponse
from app.rbac import require_admin

UPLOADS_DIR = os.getenv("UPLOADS_DIR", "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    current_user: Annotated[dict, Depends(require_admin)] = None,
    db: AsyncSession = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Allowed: pdf, docx, txt")

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    doc_id = str(uuid.uuid4())
    dest_path = os.path.join(UPLOADS_DIR, f"{doc_id}{ext}")

    contents = await file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

    # Persist document record with status=uploaded; metadata filled on /ingest
    doc = Document(
        id=doc_id,
        name=file.filename or "unknown",
        owner_department=current_user["department"],
        allowed_departments=json.dumps([current_user["department"]]),
        file_path=dest_path,
        status="uploaded",
    )
    db.add(doc)
    await db.commit()

    return UploadResponse(document_id=doc_id)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    body: IngestRequest,
    current_user: Annotated[dict, Depends(require_admin)] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == body.document_id))
    doc: Document | None = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status == "ingested":
        raise HTTPException(status_code=409, detail="Document already ingested")

    # Update metadata before ingestion
    doc.owner_department = body.owner_department
    doc.allowed_departments = json.dumps(body.allowed_departments)
    doc.classification = body.classification
    doc.document_type = body.document_type
    doc.version = body.version
    doc.status = "processing"
    await db.commit()

    try:
        from ingest.service import run_ingestion_pipeline

        chunks_stored = await run_ingestion_pipeline(
            file_path=doc.file_path,
            document_id=doc.id,
            document_name=doc.name,
            owner_department=body.owner_department,
            allowed_departments=body.allowed_departments,
            classification=body.classification,
            document_type=body.document_type,
            version=body.version,
        )
        doc.status = "ingested"
    except Exception as exc:
        doc.status = "failed"
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    await db.commit()
    return IngestResponse(document_id=doc.id, status=doc.status, chunks_stored=chunks_stored)
