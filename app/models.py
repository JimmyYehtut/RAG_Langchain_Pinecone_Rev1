from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: str
    password: str
    department: str
    role: str


class UserOut(BaseModel):
    id: str
    email: str
    department: str
    role: str

    model_config = {"from_attributes": True}


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class Citation(BaseModel):
    document_name: str
    document_id: str = ""
    chunk_index: int


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    conversation_id: str
    message_id: str


# ── Admin ─────────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    document_id: str


class IngestRequest(BaseModel):
    document_id: str
    owner_department: str
    allowed_departments: list[str]
    classification: str = "Internal"
    document_type: str = "General"
    version: str = "1.0"


class IngestResponse(BaseModel):
    document_id: str
    status: str
    chunks_stored: int


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: str
    name: str
    owner_department: str
    allowed_departments: list[str]
    classification: str
    document_type: str
    version: str
    status: str

    model_config = {"from_attributes": True}


# ── History ───────────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: str
    role: str
    content: str

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: str
    timestamp: datetime
    messages: list[MessageOut]

    model_config = {"from_attributes": True}
