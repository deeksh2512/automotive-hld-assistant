"""AUTOSAR HLD document analysis: extraction, comparison, and export."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ProjectContext, get_project_context, require_engineer
from app.api.schemas import HldCompareRequest, HldExtractRequest
from app.core.db import Artifact, Document, get_session, record_audit, save_artifact
from app.core.ingest import ingest_path
from app.modules.hld.extractor import (
    analyze_chunks,
    compare_revisions,
    consistency_findings,
    to_dot,
)

router = APIRouter(prefix="/hld", tags=["hld"])
MODULE = "hld"


def _load_document(session: Session, ctx: ProjectContext, document_id: str) -> Document:
    document = session.get(Document, document_id)
    if document is None or document.project_id != ctx.project.id:
        raise HTTPException(status_code=404, detail="Document not found in this project")
    if document.module != MODULE:
        raise HTTPException(
            status_code=400, detail=f"Document belongs to module '{document.module}', not HLD"
        )
    return document


def _analyze(document: Document):
    path = Path(document.path)
    if not path.exists():
        raise HTTPException(status_code=410, detail=f"Source file missing: {document.name}")
    chunks = ingest_path(path, document.id)
    entities, dependencies = analyze_chunks(chunks)
    return entities, dependencies


@router.post("/extract")
def extract_architecture(
    body: HldExtractRequest,
    ctx: ProjectContext = Depends(require_engineer),
    session: Session = Depends(get_session),
) -> dict:
    """Build the component, interface, port and signal inventory for a document."""
    if not body.document_id:
        raise HTTPException(status_code=400, detail="document_id is required")
    document = _load_document(session, ctx, body.document_id)
    entities, dependencies = _analyze(document)
    findings = consistency_findings(entities, dependencies)

    inventory = [entity.to_dict() for entity in entities]
    edges = [dependency.to_dict() for dependency in dependencies]

    artifact = save_artifact(
        session=session,
        project=ctx.project,
        module=MODULE,
        artifact_type="hld_entity",
        title=f"Architecture inventory: {document.name}",
        summary=f"{len(inventory)} entities and {len(edges)} dependencies extracted "
        f"from {document.name} ({document.version_label}).",
        payload={
            "document_id": document.id,
            "document_name": document.name,
            "version_label": document.version_label,
            "entities": inventory,
            "dependencies": edges,
            "findings": findings,
        },
        citations=[
            {"label": f"{document.name} p.{page}", "document_name": document.name}
            for page in sorted({p for e in entities for p in e.pages})[:12]
        ],
        confidence="high" if len(inventory) >= 5 else "medium",
        confidence_score=0.9 if len(inventory) >= 5 else 0.55,
        generation_mode="rule_based",
        actor=ctx.user,
        ref_prefix="ARCH",
    )

    counts: dict[str, int] = {}
    for entity in inventory:
        counts[entity["kind"]] = counts.get(entity["kind"], 0) + 1

    return {
        "artifact_id": artifact.id,
        "document": {"id": document.id, "name": document.name},
        "counts": counts,
        "entities": inventory,
        "dependencies": edges,
        "findings": findings,
        "dot": to_dot(entities, dependencies),
    }


@router.post("/compare")
def compare_documents(
    body: HldCompareRequest,
    ctx: ProjectContext = Depends(require_engineer),
    session: Session = Depends(get_session),
) -> dict:
    """Diff two revisions of an HLD and report what changed."""
    baseline = _load_document(session, ctx, body.baseline_document_id)
    revision = _load_document(session, ctx, body.revision_document_id)
    baseline_entities, baseline_deps = _analyze(baseline)
    revision_entities, revision_deps = _analyze(revision)

    diff = compare_revisions(baseline_entities, revision_entities)

    base_edges = {(d.source, d.target, d.relation) for d in baseline_deps}
    rev_edges = {(d.source, d.target, d.relation) for d in revision_deps}
    diff["dependencies_added"] = [
        {"source": s, "target": t, "relation": r} for s, t, r in sorted(rev_edges - base_edges)
    ]
    diff["dependencies_removed"] = [
        {"source": s, "target": t, "relation": r} for s, t, r in sorted(base_edges - rev_edges)
    ]

    record_audit(
        session,
        action="hld.compared",
        actor=ctx.user,
        project_id=ctx.project.id,
        module=MODULE,
        detail=f"{baseline.name} ({baseline.version_label}) vs "
        f"{revision.name} ({revision.version_label})",
    )

    return {
        "baseline": {"id": baseline.id, "name": baseline.name, "version": baseline.version_label},
        "revision": {"id": revision.id, "name": revision.name, "version": revision.version_label},
        "summary": {
            "added": len(diff["added"]),
            "removed": len(diff["removed"]),
            "changed": len(diff["changed"]),
            "dependencies_added": len(diff["dependencies_added"]),
            "dependencies_removed": len(diff["dependencies_removed"]),
        },
        **diff,
    }


@router.get("/export")
def export_inventory(
    artifact_id: str,
    fmt: str = "csv",
    ctx: ProjectContext = Depends(get_project_context),
    session: Session = Depends(get_session),
):
    """Export a stored inventory for downstream tooling."""
    artifact = session.get(Artifact, artifact_id)
    if artifact is None or artifact.project_id != ctx.project.id:
        raise HTTPException(status_code=404, detail="Artifact not found in this project")
    entities = (artifact.payload or {}).get("entities", [])

    if fmt == "json":
        return StreamingResponse(
            io.BytesIO(json.dumps(artifact.payload, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{artifact.ref}.json"'},
        )

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["name", "kind", "detail", "pages", "sections", "occurrences", "evidence"])
    for entity in entities:
        writer.writerow(
            [
                entity.get("name", ""),
                entity.get("kind", ""),
                entity.get("detail", ""),
                ";".join(str(p) for p in entity.get("pages", [])),
                " / ".join(entity.get("sections", [])),
                entity.get("occurrences", 0),
                (entity.get("evidence", "") or "").replace("\n", " ")[:200],
            ]
        )
    return StreamingResponse(
        io.BytesIO(buffer.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{artifact.ref}.csv"'},
    )


@router.get("/inventories")
def list_inventories(
    ctx: ProjectContext = Depends(get_project_context),
    session: Session = Depends(get_session),
) -> list[dict]:
    artifacts = session.scalars(
        select(Artifact)
        .where(
            Artifact.project_id == ctx.project.id,
            Artifact.artifact_type == "hld_entity",
        )
        .order_by(Artifact.created_at.desc())
    ).all()
    return [
        {
            "id": artifact.id,
            "ref": artifact.ref,
            "title": artifact.title,
            "entity_count": len((artifact.payload or {}).get("entities", [])),
            "finding_count": len((artifact.payload or {}).get("findings", [])),
            "review_status": artifact.review_status,
            "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
        }
        for artifact in artifacts
    ]
