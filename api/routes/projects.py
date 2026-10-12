"""Project management endpoints."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database.models import Project
from api.database.session import get_db
from api.schemas import ProjectCreate, ProjectPatch, ProjectResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, session: Session = Depends(get_db)) -> Project:
    project = Project(id=str(uuid4()), name=body.name, description=body.description)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse])
def list_projects(limit: int = Query(default=50, ge=1, le=200), session: Session = Depends(get_db)) -> list[Project]:
    return list(session.scalars(select(Project).order_by(Project.created_at.desc()).limit(limit)).all())


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, session: Session = Depends(get_db)) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(404, detail={"code": "project_not_found", "message": "Project not found."})
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def patch_project(project_id: str, body: ProjectPatch, session: Session = Depends(get_db)) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(404, detail={"code": "project_not_found", "message": "Project not found."})
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(422, detail={"code": "empty_patch", "message": "Provide at least one field to update."})
    if "name" in changes and changes["name"] is None:
        raise HTTPException(422, detail={"code": "invalid_project_name", "message": "Project name cannot be null."})
    for key, value in changes.items():
        setattr(project, key, value)
    session.commit()
    session.refresh(project)
    return project
