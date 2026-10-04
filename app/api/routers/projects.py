"""Project workspaces and their membership-based access control."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import Identity, ProjectContext, get_identity, get_project_context
from app.api.schemas import ProjectCreate, ProjectOut
from app.core.db import (
    Artifact,
    Document,
    Membership,
    Project,
    get_project_by_key,
    get_session,
    new_id,
    record_audit,
)
from app.core.vectorstore import slugify

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_out(session: Session, project: Project) -> ProjectOut:
    documents = session.scalar(
        select(func.count(Document.id)).where(Document.project_id == project.id)
    )
    artifacts = session.scalar(
        select(func.count(Artifact.id)).where(Artifact.project_id == project.id)
    )
    return ProjectOut(
        id=project.id,
        key=project.key,
        name=project.name,
        description=project.description,
        classification=project.classification,
        document_count=documents or 0,
        artifact_count=artifacts or 0,
    )


@router.get("", response_model=list[ProjectOut])
def list_projects(session: Session = Depends(get_session)) -> list[ProjectOut]:
    projects = session.scalars(select(Project).order_by(Project.created_at)).all()
    return [_to_out(session, project) for project in projects]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    body: ProjectCreate,
    session: Session = Depends(get_session),
    identity: Identity = Depends(get_identity),
) -> ProjectOut:
    key = slugify(body.key)
    if get_project_by_key(session, key) is not None:
        raise HTTPException(status_code=409, detail=f"Project '{key}' already exists")
    project = Project(
        id=new_id("prj"),
        key=key,
        name=body.name,
        description=body.description,
        classification=body.classification,
    )
    session.add(project)
    session.flush()
    session.add(
        Membership(id=new_id("mem"), project_id=project.id, user=identity.user, role="admin")
    )
    record_audit(
        session,
        action="project.created",
        actor=identity.user,
        project_id=project.id,
        detail=f"{project.key} ({project.classification})",
    )
    return _to_out(session, project)


@router.get("/members")
def list_members(
    ctx: ProjectContext = Depends(get_project_context),
    session: Session = Depends(get_session),
) -> dict:
    members = session.scalars(
        select(Membership).where(Membership.project_id == ctx.project.id)
    ).all()
    return {
        "project": ctx.key,
        "your_role": ctx.role,
        "members": [{"user": m.user, "role": m.role} for m in members],
    }
