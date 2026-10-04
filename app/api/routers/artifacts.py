"""Artifact listing, the human review queue, and traceability links."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ProjectContext, get_project_context, require_approver
from app.api.schemas import ArtifactOut, ReviewRequest
from app.core.db import (
    Artifact,
    Review,
    TraceLink,
    get_session,
    new_id,
    record_audit,
)

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("", response_model=list[ArtifactOut])
def list_artifacts(
    module: str | None = None,
    artifact_type: str | None = None,
    review_status: str | None = None,
    limit: int = 500,
    ctx: ProjectContext = Depends(get_project_context),
    session: Session = Depends(get_session),
) -> list[ArtifactOut]:
    statement = select(Artifact).where(Artifact.project_id == ctx.project.id)
    if module:
        statement = statement.where(Artifact.module == module)
    if artifact_type:
        statement = statement.where(Artifact.artifact_type == artifact_type)
    if review_status:
        statement = statement.where(Artifact.review_status == review_status)
    artifacts = session.scalars(statement.order_by(Artifact.created_at).limit(limit)).all()
    return [ArtifactOut(**artifact.to_dict()) for artifact in artifacts]


@router.get("/{artifact_id}", response_model=ArtifactOut)
def get_artifact(
    artifact_id: str,
    ctx: ProjectContext = Depends(get_project_context),
    session: Session = Depends(get_session),
) -> ArtifactOut:
    artifact = session.get(Artifact, artifact_id)
    if artifact is None or artifact.project_id != ctx.project.id:
        raise HTTPException(status_code=404, detail="Artifact not found in this project")
    return ArtifactOut(**artifact.to_dict())


@router.post("/{artifact_id}/review", response_model=ArtifactOut)
def review_artifact(
    artifact_id: str,
    body: ReviewRequest,
    ctx: ProjectContext = Depends(require_approver),
    session: Session = Depends(get_session),
) -> ArtifactOut:
    """Record the mandatory human disposition on an AI-assisted artifact."""
    artifact = session.get(Artifact, artifact_id)
    if artifact is None or artifact.project_id != ctx.project.id:
        raise HTTPException(status_code=404, detail="Artifact not found in this project")

    if body.edited_payload is not None:
        artifact.payload = body.edited_payload
    if body.edited_summary is not None:
        artifact.summary = body.edited_summary

    artifact.review_status = {
        "accepted": "approved",
        "edited": "approved_with_edits",
        "rejected": "rejected",
    }[body.decision]

    session.add(
        Review(
            id=new_id("rev"),
            artifact_id=artifact.id,
            decision=body.decision,
            comment=body.comment,
            reviewer=ctx.user,
        )
    )
    record_audit(
        session,
        action="artifact.reviewed",
        actor=ctx.user,
        project_id=ctx.project.id,
        module=artifact.module,
        detail=f"{artifact.ref} -> {artifact.review_status}. {body.comment[:300]}",
        meta={"artifact_id": artifact.id, "decision": body.decision},
    )
    session.flush()
    return ArtifactOut(**artifact.to_dict())


@router.get("/{artifact_id}/history")
def artifact_history(
    artifact_id: str,
    ctx: ProjectContext = Depends(get_project_context),
    session: Session = Depends(get_session),
) -> list[dict]:
    artifact = session.get(Artifact, artifact_id)
    if artifact is None or artifact.project_id != ctx.project.id:
        raise HTTPException(status_code=404, detail="Artifact not found in this project")
    return [
        {
            "decision": review.decision,
            "comment": review.comment,
            "reviewer": review.reviewer,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        }
        for review in artifact.reviews
    ]


@router.post("/link", status_code=201)
def create_link(
    source_id: str,
    target_id: str,
    link_type: str = "derives",
    ctx: ProjectContext = Depends(get_project_context),
    session: Session = Depends(get_session),
) -> dict:
    for artifact_id in (source_id, target_id):
        artifact = session.get(Artifact, artifact_id)
        if artifact is None or artifact.project_id != ctx.project.id:
            raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")
    link = TraceLink(
        id=new_id("lnk"),
        project_id=ctx.project.id,
        source_id=source_id,
        target_id=target_id,
        link_type=link_type,
    )
    session.add(link)
    record_audit(
        session,
        action="trace.linked",
        actor=ctx.user,
        project_id=ctx.project.id,
        detail=f"{source_id} -{link_type}-> {target_id}",
    )
    return {"id": link.id, "source_id": source_id, "target_id": target_id, "link_type": link_type}


@router.get("/trace/matrix")
def trace_matrix(
    ctx: ProjectContext = Depends(get_project_context),
    session: Session = Depends(get_session),
) -> dict:
    """Flatten artifacts and links into a reviewable traceability matrix."""
    artifacts = session.scalars(
        select(Artifact).where(Artifact.project_id == ctx.project.id)
    ).all()
    links = session.scalars(
        select(TraceLink).where(TraceLink.project_id == ctx.project.id)
    ).all()
    index = {artifact.id: artifact for artifact in artifacts}

    rows = []
    for link in links:
        source = index.get(link.source_id)
        target = index.get(link.target_id)
        if not source or not target:
            continue
        rows.append(
            {
                "source_ref": source.ref,
                "source_type": source.artifact_type,
                "source_title": source.title,
                "link_type": link.link_type,
                "target_ref": target.ref,
                "target_type": target.artifact_type,
                "target_title": target.title,
                "target_status": target.review_status,
            }
        )

    linked_ids = {link.source_id for link in links} | {link.target_id for link in links}
    orphans = [
        {"ref": a.ref, "type": a.artifact_type, "title": a.title}
        for a in artifacts
        if a.id not in linked_ids and a.artifact_type != "qa_answer"
    ]
    total = len([a for a in artifacts if a.artifact_type != "qa_answer"])
    completeness = round(100 * (total - len(orphans)) / total, 1) if total else 0.0
    return {
        "rows": rows,
        "unlinked": orphans,
        "link_completeness_percent": completeness,
        "artifact_count": total,
    }
