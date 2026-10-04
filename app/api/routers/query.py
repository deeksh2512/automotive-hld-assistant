"""Cited natural-language Q&A across any module collection."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import ProjectContext, get_project_context
from app.api.schemas import AnswerOut, QueryRequest
from app.core.db import get_session, record_audit, save_artifact
from app.core.rag import answer_question

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=AnswerOut)
def ask(
    body: QueryRequest,
    ctx: ProjectContext = Depends(get_project_context),
    session: Session = Depends(get_session),
) -> AnswerOut:
    where = {"document_id": body.document_id} if body.document_id else None
    result = answer_question(
        project_key=ctx.key,
        module=body.module,
        question=body.question,
        top_k=body.top_k,
        where=where,
    )

    record_audit(
        session,
        action="query.answered",
        actor=ctx.user,
        project_id=ctx.project.id,
        module=body.module,
        detail=body.question[:500],
        meta={
            "confidence": result.confidence,
            "mode": result.mode,
            "citations": len(result.citations),
        },
    )

    artifact_id = None
    # Only durable, grounded answers enter the review queue.
    if result.citations and result.mode == "generated":
        artifact = save_artifact(
            session=session,
            project=ctx.project,
            module=body.module,
            artifact_type="qa_answer",
            title=body.question[:200],
            summary=result.answer,
            payload={"question": body.question, "warnings": result.warnings},
            citations=[c.__dict__ for c in result.citations],
            confidence=result.confidence,
            confidence_score=result.confidence_score,
            generation_mode=result.mode,
            actor=ctx.user,
            ref_prefix="QA",
        )
        artifact_id = artifact.id

    payload = result.to_dict()
    payload["artifact_id"] = artifact_id
    return AnswerOut(**payload)
