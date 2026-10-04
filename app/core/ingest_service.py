"""Orchestrates upload -> parse -> chunk -> embed -> index -> record."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.core.db import Document, Project, new_id, record_audit
from app.core.ingest import SUPPORTED_EXTENSIONS, IngestionError, file_checksum, ingest_path
from app.core.vectorstore import get_vector_store

logger = logging.getLogger(__name__)


def store_upload(project_key: str, filename: str, data: bytes) -> Path:
    safe_name = Path(filename).name.replace("..", "_")
    target_dir = Path(settings.upload_dir) / project_key
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_name
    counter = 1
    while target.exists():
        target = target_dir / f"{Path(safe_name).stem}_{counter}{Path(safe_name).suffix}"
        counter += 1
    target.write_bytes(data)
    return target


def ingest_document(
    session: Session,
    project: Project,
    module: str,
    path: Path,
    actor: str,
    doc_type: str = "document",
    version_label: str = "v1",
    approved_source: bool = False,
    display_name: str | None = None,
) -> Document:
    """Index a file into the project's module collection and persist its record."""
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise IngestionError(f"Unsupported file type '{path.suffix}' for {path.name}")

    document = Document(
        id=new_id("doc"),
        project_id=project.id,
        module=module,
        name=display_name or path.name,
        path=str(path),
        doc_type=doc_type,
        version_label=version_label,
        approved_source=approved_source,
        checksum=file_checksum(path),
        uploaded_by=actor,
        status="processing",
    )
    session.add(document)
    session.flush()

    try:
        chunks = ingest_path(path, document.id)
        if not chunks:
            raise IngestionError("Parsing produced no indexable content.")
        base_metadata = {
            "project_key": project.key,
            "project_id": project.id,
            "module": module,
            "document_id": document.id,
            "document_name": document.name,
            "doc_type": doc_type,
            "version_label": version_label,
            "approved_source": approved_source,
        }
        indexed = get_vector_store().add_chunks(project.key, module, chunks, base_metadata)
        document.chunk_count = indexed
        document.page_count = max((c.page_end for c in chunks), default=0)
        document.status = "indexed"
    except Exception as exc:
        document.status = "failed"
        document.error = str(exc)[:1000]
        logger.exception("Ingestion failed for %s", path)
        record_audit(
            session,
            action="document.ingest.failed",
            actor=actor,
            project_id=project.id,
            module=module,
            detail=f"{document.name}: {exc}",
        )
        return document

    record_audit(
        session,
        action="document.ingested",
        actor=actor,
        project_id=project.id,
        module=module,
        detail=f"{document.name} ({document.chunk_count} chunks, {document.page_count} pages)",
        meta={"document_id": document.id, "checksum": document.checksum},
    )
    return document


def delete_document(session: Session, project: Project, document: Document, actor: str) -> None:
    get_vector_store().delete_document(project.key, document.module, document.id)
    stored = Path(document.path)
    if stored.exists() and str(stored).startswith(str(Path(settings.upload_dir).resolve())):
        try:
            stored.unlink()
        except OSError:
            pass
    record_audit(
        session,
        action="document.deleted",
        actor=actor,
        project_id=project.id,
        module=document.module,
        detail=document.name,
    )
    session.delete(document)


def copy_sample_into_project(sample: Path, project_key: str) -> Path:
    target_dir = Path(settings.upload_dir) / project_key
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / sample.name
    if not target.exists():
        shutil.copy2(sample, target)
    return target
