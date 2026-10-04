"""Pydantic request/response models shared by the routers."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    key: str = Field(..., min_length=2, max_length=64)
    name: str
    description: str = ""
    classification: str = "internal"


class ProjectOut(BaseModel):
    id: str
    key: str
    name: str
    description: str
    classification: str
    document_count: int = 0
    artifact_count: int = 0


class DocumentOut(BaseModel):
    id: str
    name: str
    module: str
    doc_type: str
    version_label: str
    approved_source: bool
    chunk_count: int
    status: str
    error: str = ""
    created_at: str | None = None


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    module: str = "hld"
    top_k: int | None = None
    document_id: str | None = None


class CitationOut(BaseModel):
    marker: str
    chunk_id: str
    label: str
    document_name: str
    page_start: int | None = None
    page_end: int | None = None
    heading_path: str = ""
    score: float = 0.0
    excerpt: str = ""


class AnswerOut(BaseModel):
    answer: str
    citations: list[CitationOut] = []
    sources: list[CitationOut] = []
    confidence: str
    confidence_score: float
    mode: str
    warnings: list[str] = []
    review_status: str = "pending_review"
    artifact_id: str | None = None


class ArtifactOut(BaseModel):
    id: str
    module: str
    artifact_type: str
    ref: str
    title: str
    summary: str
    payload: dict[str, Any] = {}
    citations: list[Any] = []
    confidence: str
    confidence_score: float
    generation_mode: str
    review_status: str
    created_by: str
    created_at: str | None = None


class ReviewRequest(BaseModel):
    decision: Literal["accepted", "edited", "rejected"]
    comment: str = ""
    edited_payload: dict[str, Any] | None = None
    edited_summary: str | None = None


class HealthOut(BaseModel):
    status: str
    version: str
    llm_available: bool
    llm_provider: str
    llm_model: str
    llm_detail: str
    embeddings_ready: bool
    vectorstore_ready: bool
    embedding_model: str
    modules: list[str]


# --- Module-specific -------------------------------------------------------


class HldExtractRequest(BaseModel):
    document_id: str | None = None


class HldCompareRequest(BaseModel):
    baseline_document_id: str
    revision_document_id: str
