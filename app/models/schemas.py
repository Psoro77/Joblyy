from datetime import datetime
from pydantic import BaseModel


# ── Jobs ──

class JobCreate(BaseModel):
    title: str
    company: str
    url: str
    description: str | None = None
    source: str | None = None
    match_score: float | None = None


class JobUpdate(BaseModel):
    status: str | None = None
    match_score: float | None = None
    title: str | None = None
    company: str | None = None
    description: str | None = None


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    url: str
    description: str | None
    source: str | None
    match_score: float | None
    status: str
    found_at: datetime


# ── Applications ──

class ApplicationCreate(BaseModel):
    job_id: int
    method: str = "manual"
    notes: str | None = None


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    applied_at: datetime | None
    method: str
    status: str
    notes: str | None


# ── Conversations ──

class MessageCreate(BaseModel):
    role: str
    content: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


# ── Chat ──

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


# ── Memory / Markdown ──

class MarkdownContent(BaseModel):
    content: str
