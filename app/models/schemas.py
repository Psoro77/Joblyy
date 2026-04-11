from typing import Optional
from datetime import datetime
from pydantic import BaseModel


# ── Jobs ──

class JobCreate(BaseModel):
    title: str
    company: str
    url: str
    description: Optional[str] = None
    source: Optional[str] = None
    match_score: Optional[float] = None


class JobUpdate(BaseModel):
    status: Optional[str] = None
    match_score: Optional[float] = None
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    url: str
    description: Optional[str]
    source: Optional[str]
    match_score: Optional[float]
    status: str
    found_at: datetime


# ── Applications ──

class ApplicationCreate(BaseModel):
    job_id: int
    method: str = "manual"
    notes: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    applied_at: Optional[datetime]
    method: str
    status: str
    notes: Optional[str]


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


# ── Settings ──

class SettingsUpdate(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None


class SettingsResponse(BaseModel):
    provider: str
    model: str
    ollama_base_url: str


# ── Memory / Markdown ──

class MarkdownContent(BaseModel):
    content: str
