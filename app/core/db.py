"""SQLite persistence: projects, documents, artifacts, reviews, audit log, RBAC."""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from app.config import settings

# Role hierarchy used for every authorization check in the API layer.
ROLES = ("viewer", "engineer", "approver", "admin")
ROLE_LEVEL = {role: index for index, role in enumerate(ROLES)}

MODULES = ("hld",)

ARTIFACT_TYPES = (
    "hld_entity",
    "hld_finding",
    "qa_answer",
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    classification: Mapped[str] = mapped_column(String(40), default="internal")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    documents: Mapped[list["Document"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Membership(Base):
    """Per-project role assignment (the document's project-isolation control)."""

    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    user: Mapped[str] = mapped_column(String(160), index=True)
    role: Mapped[str] = mapped_column(String(20), default="engineer")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="memberships")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    module: Mapped[str] = mapped_column(String(24), index=True)
    name: Mapped[str] = mapped_column(String(300))
    path: Mapped[str] = mapped_column(Text)
    doc_type: Mapped[str] = mapped_column(String(40), default="document")
    version_label: Mapped[str] = mapped_column(String(60), default="v1")
    approved_source: Mapped[bool] = mapped_column(Boolean, default=False)
    checksum: Mapped[str] = mapped_column(String(64), default="")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="indexed")
    error: Mapped[str] = mapped_column(Text, default="")
    uploaded_by: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="documents")


class Artifact(Base):
    """Polymorphic engineering output: hazard, threat, finding, test case, answer."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    module: Mapped[str] = mapped_column(String(24), index=True)
    artifact_type: Mapped[str] = mapped_column(String(40), index=True)
    ref: Mapped[str] = mapped_column(String(60), default="")
    title: Mapped[str] = mapped_column(String(400), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    citations: Mapped[list[Any]] = mapped_column(JSON, default=list)
    confidence: Mapped[str] = mapped_column(String(16), default="low")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    generation_mode: Mapped[str] = mapped_column(String(24), default="rule_based")
    review_status: Mapped[str] = mapped_column(String(24), default="pending_review", index=True)
    created_by: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    project: Mapped[Project] = relationship(back_populates="artifacts")
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="artifact", cascade="all, delete-orphan"
    )
    links_out: Mapped[list["TraceLink"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
        foreign_keys="TraceLink.source_id",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "module": self.module,
            "artifact_type": self.artifact_type,
            "ref": self.ref,
            "title": self.title,
            "summary": self.summary,
            "payload": self.payload or {},
            "citations": self.citations or [],
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "generation_mode": self.generation_mode,
            "review_status": self.review_status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), index=True)
    decision: Mapped[str] = mapped_column(String(24))  # accepted | edited | rejected
    comment: Mapped[str] = mapped_column(Text, default="")
    reviewer: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    artifact: Mapped[Artifact] = relationship(back_populates="reviews")


class TraceLink(Base):
    """Cross-artifact traceability (hazard -> safety goal -> requirement -> test)."""

    __tablename__ = "trace_links"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), index=True)
    target_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), index=True)
    link_type: Mapped[str] = mapped_column(String(40), default="derives")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    source: Mapped[Artifact] = relationship(
        back_populates="links_out", foreign_keys=[source_id]
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    module: Mapped[str] = mapped_column(String(24), default="")
    action: Mapped[str] = mapped_column(String(60), index=True)
    actor: Mapped[str] = mapped_column(String(160), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


_engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    future=True,
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    settings.ensure_directories()
    Base.metadata.create_all(_engine)
    with session_scope() as session:
        exists = session.scalar(select(Project).where(Project.key == "demo-ecu"))
        if exists is None:
            seed_demo_project(session)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def seed_demo_project(session: Session) -> Project:
    project = Project(
        id=new_id("prj"),
        key="demo-ecu",
        name="Demo Body Control ECU",
        description="Sample workspace preloaded for evaluating the HLD assistant.",
        classification="internal",
    )
    session.add(project)
    session.flush()
    for user, role in (
        (settings.default_user, "admin"),
        ("viewer@local", "viewer"),
        ("approver@local", "approver"),
    ):
        session.add(
            Membership(id=new_id("mem"), project_id=project.id, user=user, role=role)
        )
    session.add(
        AuditLog(
            id=new_id("log"),
            project_id=project.id,
            action="project.seeded",
            actor="system",
            detail="Demo project created on first start.",
        )
    )
    return project


# --------------------------------------------------------------------------
# Helpers used across routers
# --------------------------------------------------------------------------


def record_audit(
    session: Session,
    action: str,
    actor: str,
    project_id: str = "",
    module: str = "",
    detail: str = "",
    meta: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            id=new_id("log"),
            project_id=project_id,
            module=module,
            action=action,
            actor=actor,
            detail=detail[:2000],
            meta=meta or {},
        )
    )


def get_project_by_key(session: Session, key: str) -> Project | None:
    return session.scalar(select(Project).where(Project.key == key))


def effective_role(session: Session, project: Project, user: str) -> str:
    membership = session.scalar(
        select(Membership).where(
            Membership.project_id == project.id, Membership.user == user
        )
    )
    return membership.role if membership else settings.default_role


def role_allows(role: str, required: str) -> bool:
    return ROLE_LEVEL.get(role, -1) >= ROLE_LEVEL.get(required, 99)


def next_ref(session: Session, project_id: str, artifact_type: str, prefix: str) -> str:
    count = len(
        session.scalars(
            select(Artifact.id).where(
                Artifact.project_id == project_id, Artifact.artifact_type == artifact_type
            )
        ).all()
    )
    return f"{prefix}-{count + 1:03d}"


def save_artifact(
    session: Session,
    project: Project,
    module: str,
    artifact_type: str,
    title: str,
    summary: str,
    payload: dict[str, Any],
    citations: list[Any],
    confidence: str,
    confidence_score: float,
    generation_mode: str,
    actor: str,
    ref_prefix: str = "ART",
) -> Artifact:
    artifact = Artifact(
        id=new_id("art"),
        project_id=project.id,
        module=module,
        artifact_type=artifact_type,
        ref=next_ref(session, project.id, artifact_type, ref_prefix),
        title=title[:400],
        summary=summary,
        payload=payload,
        citations=json.loads(json.dumps(citations, default=str)),
        confidence=confidence,
        confidence_score=confidence_score,
        generation_mode=generation_mode,
        created_by=actor,
    )
    session.add(artifact)
    session.flush()
    record_audit(
        session,
        action=f"{module}.artifact.created",
        actor=actor,
        project_id=project.id,
        module=module,
        detail=f"{artifact_type} {artifact.ref}: {title[:120]}",
        meta={"artifact_id": artifact.id, "confidence": confidence},
    )
    return artifact
