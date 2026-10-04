"""Request dependencies: identity, project resolution, role enforcement.

Pilot identity is header-based (`X-User`), which is the seam an enterprise IAM
would replace. Authorization itself is already project-scoped.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.db import (
    Project,
    effective_role,
    get_project_by_key,
    get_session,
    role_allows,
)


@dataclass
class Identity:
    user: str
    role: str


def get_identity(x_user: str | None = Header(default=None, alias="X-User")) -> Identity:
    return Identity(user=x_user or settings.default_user, role=settings.default_role)


@dataclass
class ProjectContext:
    project: Project
    identity: Identity
    role: str

    @property
    def key(self) -> str:
        return self.project.key

    @property
    def user(self) -> str:
        return self.identity.user

    def require(self, required_role: str) -> None:
        if not role_allows(self.role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{self.role}' cannot perform this action; '{required_role}' required.",
            )


def get_project_context(
    project: str = Query(..., description="Project key"),
    session: Session = Depends(get_session),
    identity: Identity = Depends(get_identity),
) -> ProjectContext:
    record = get_project_by_key(session, project)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Unknown project '{project}'")
    role = effective_role(session, record, identity.user)
    return ProjectContext(project=record, identity=identity, role=role)


def require_engineer(ctx: ProjectContext = Depends(get_project_context)) -> ProjectContext:
    ctx.require("engineer")
    return ctx


def require_approver(ctx: ProjectContext = Depends(get_project_context)) -> ProjectContext:
    ctx.require("approver")
    return ctx
