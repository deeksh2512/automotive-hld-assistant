"""Health, model status, and audit trail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app import __version__
from app.api.schemas import HealthOut
from app.config import settings
from app.core.db import MODULES, AuditLog, get_session
from app.core.embeddings import get_embedding_service
from app.core.llm import get_llm_status
from app.core.vectorstore import get_vector_store

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    llm = get_llm_status()
    return HealthOut(
        status="ok",
        version=__version__,
        llm_available=llm.available,
        llm_provider=llm.provider,
        llm_model=llm.model,
        llm_detail=llm.detail,
        embeddings_ready=get_embedding_service().is_ready(),
        vectorstore_ready=get_vector_store().is_ready(),
        embedding_model=settings.embedding_model,
        modules=list(MODULES),
    )


@router.get("/audit")
def audit_log(
    project: str | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
    session: Session = Depends(get_session),
) -> list[dict]:
    statement = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    entries = session.scalars(statement).all()
    return [
        {
            "id": entry.id,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "action": entry.action,
            "actor": entry.actor,
            "module": entry.module,
            "project_id": entry.project_id,
            "detail": entry.detail,
            "meta": entry.meta or {},
        }
        for entry in entries
    ]
