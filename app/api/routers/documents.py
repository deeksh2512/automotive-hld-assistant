"""Document upload, listing, deletion, and sample loading."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ProjectContext, get_project_context, require_engineer
from app.api.schemas import DocumentOut
from app.config import PROJECT_ROOT
from app.core.db import Document, get_session
from app.core.ingest import SUPPORTED_EXTENSIONS
from app.core.ingest_service import (
    copy_sample_into_project,
    delete_document,
    ingest_document,
    store_upload,
)

router = APIRouter(prefix="/documents", tags=["documents"])

SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"

# Sample files shipped with the assistant. Two revisions of one design so the
# comparison feature is demonstrable out of the box.
SAMPLE_MANIFEST: list[dict[str, str]] = [
    {"file": "sample_hld_body_control.md", "module": "hld", "doc_type": "hld"},
    {"file": "sample_hld_body_control_rev_b.md", "module": "hld", "doc_type": "hld"},
]


def _to_out(document: Document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        name=document.name,
        module=document.module,
        doc_type=document.doc_type,
        version_label=document.version_label,
        approved_source=document.approved_source,
        chunk_count=document.chunk_count,
        status=document.status,
        error=document.error,
        created_at=document.created_at.isoformat() if document.created_at else None,
    )


@router.get("", response_model=list[DocumentOut])
def list_documents(
    module: str | None = None,
    ctx: ProjectContext = Depends(get_project_context),
    session: Session = Depends(get_session),
) -> list[DocumentOut]:
    statement = select(Document).where(Document.project_id == ctx.project.id)
    if module:
        statement = statement.where(Document.module == module)
    documents = session.scalars(statement.order_by(Document.created_at)).all()
    return [_to_out(document) for document in documents]


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    module: str = Form("hld"),
    doc_type: str = Form("document"),
    version_label: str = Form("v1"),
    approved_source: bool = Form(False),
    ctx: ProjectContext = Depends(require_engineer),
    session: Session = Depends(get_session),
) -> DocumentOut:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    path = store_upload(ctx.key, file.filename or "upload", data)
    document = ingest_document(
        session=session,
        project=ctx.project,
        module=module,
        path=path,
        actor=ctx.user,
        doc_type=doc_type,
        version_label=version_label,
        approved_source=approved_source,
    )
    return _to_out(document)


@router.post("/load-samples", response_model=list[DocumentOut])
def load_samples(
    module: str | None = None,
    ctx: ProjectContext = Depends(require_engineer),
    session: Session = Depends(get_session),
) -> list[DocumentOut]:
    """Index the bundled synthetic design documents."""
    existing = {
        document.name
        for document in session.scalars(
            select(Document).where(Document.project_id == ctx.project.id)
        ).all()
    }
    results: list[DocumentOut] = []
    for entry in SAMPLE_MANIFEST:
        if module and entry["module"] != module:
            continue
        source = SAMPLES_DIR / entry["file"]
        if not source.exists() or entry["file"] in existing:
            continue
        path = copy_sample_into_project(source, ctx.key)
        document = ingest_document(
            session=session,
            project=ctx.project,
            module=entry["module"],
            path=path,
            actor=ctx.user,
            doc_type=entry["doc_type"],
            version_label="rev-b" if "rev_b" in entry["file"] else "rev-a",
            approved_source=True,
        )
        results.append(_to_out(document))
    return results


@router.delete("/{document_id}", status_code=204, response_class=Response)
def remove_document(
    document_id: str,
    ctx: ProjectContext = Depends(require_engineer),
    session: Session = Depends(get_session),
) -> Response:
    document = session.get(Document, document_id)
    if document is None or document.project_id != ctx.project.id:
        raise HTTPException(status_code=404, detail="Document not found in this project")
    delete_document(session, ctx.project, document, ctx.user)
    return Response(status_code=204)
