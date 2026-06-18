"""
项目管理 API - 项目CRUD、文件上传、评分标准管理
"""
import os
import json
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import (
    Project, ProjectDocument, ScoringCriteria, ReviewTask
)
from app.schemas.project import (
    ProjectCreate, ProjectResponse, ProjectDetail,
    DocumentResponse, ScoringCriteriaCreate, ScoringCriteriaResponse,
)

router = APIRouter()


# --- Project CRUD ---

@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all projects for the current user."""
    result = await db.execute(
        select(Project).where(Project.created_by == current_user.id).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    response = []
    for p in projects:
        # Count documents and tasks
        doc_count = await db.execute(
            select(func.count(ProjectDocument.id)).where(ProjectDocument.project_id == p.id)
        )
        task_count = await db.execute(
            select(func.count(ReviewTask.id)).where(ReviewTask.project_id == p.id)
        )
        resp = ProjectResponse(
            **{k: getattr(p, k) for k in ProjectResponse.model_fields},
            document_count=doc_count.scalar() or 0,
            task_count=task_count.scalar() or 0,
        )
        response.append(resp)
    return response


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new project."""
    project = Project(
        name=data.name,
        description=data.description,
        bid_number=data.bid_number,
        created_by=current_user.id,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return ProjectResponse(
        **{k: getattr(project, k) for k in ProjectResponse.model_fields},
        document_count=0,
        task_count=0,
    )


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get project detail with documents and scoring criteria."""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.documents), selectinload(Project.scoring_criteria))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此项目")

    doc_count = await db.execute(
        select(func.count(ProjectDocument.id)).where(ProjectDocument.project_id == project_id)
    )
    task_count = await db.execute(
        select(func.count(ReviewTask.id)).where(ReviewTask.project_id == project_id)
    )

    return ProjectDetail(
        **{k: getattr(project, k) for k in ProjectResponse.model_fields},
        document_count=doc_count.scalar() or 0,
        task_count=task_count.scalar() or 0,
        documents=[DocumentResponse.model_validate(d) for d in project.documents],
        scoring_criteria=[ScoringCriteriaResponse.model_validate(s) for s in project.scoring_criteria],
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a project and all its associated data."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此项目")

    await db.delete(project)
    return {"message": "项目已删除"}


# --- Document Upload ---

@router.post("/{project_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    doc_type: str = Form("tender_doc"),  # scoring_criteria, tender_doc, supplementary
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a document to a project."""
    # Verify project exists and user has access
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此项目")

    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".doc", ".txt"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")

    # Save file
    project_dir = os.path.join(settings.UPLOAD_DIR, str(project_id))
    os.makedirs(project_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{ext}"
    file_path = os.path.join(project_dir, safe_filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Create document record
    doc = ProjectDocument(
        project_id=project_id,
        doc_type=doc_type,
        filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        status="uploaded",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Trigger background parsing
    from app.tasks.document_tasks import parse_document_task
    background_tasks = BackgroundTasks()
    background_tasks.add_task(parse_document_task, doc.id)

    return DocumentResponse.model_validate(doc)


# --- Scoring Criteria ---

@router.get("/{project_id}/criteria", response_model=List[ScoringCriteriaResponse])
async def list_criteria(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List scoring criteria for a project."""
    result = await db.execute(
        select(ScoringCriteria)
        .where(ScoringCriteria.project_id == project_id)
        .order_by(ScoringCriteria.sort_order)
    )
    return [ScoringCriteriaResponse.model_validate(c) for c in result.scalars().all()]


@router.post("/{project_id}/criteria", response_model=ScoringCriteriaResponse, status_code=201)
async def create_criteria(
    project_id: int,
    data: ScoringCriteriaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually add a scoring criteria item."""
    criteria = ScoringCriteria(
        project_id=project_id,
        **data.model_dump(),
    )
    db.add(criteria)
    await db.flush()
    await db.refresh(criteria)
    return ScoringCriteriaResponse.model_validate(criteria)


@router.post("/{project_id}/criteria/batch", response_model=List[ScoringCriteriaResponse])
async def batch_create_criteria(
    project_id: int,
    items: List[ScoringCriteriaCreate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch create scoring criteria items."""
    created = []
    for item in items:
        criteria = ScoringCriteria(
            project_id=project_id,
            **item.model_dump(),
        )
        db.add(criteria)
        await db.flush()
        await db.refresh(criteria)
        created.append(ScoringCriteriaResponse.model_validate(criteria))
    return created


@router.delete("/{project_id}/criteria/{criteria_id}")
async def delete_criteria(
    project_id: int,
    criteria_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a scoring criteria item."""
    result = await db.execute(
        select(ScoringCriteria).where(
            ScoringCriteria.id == criteria_id,
            ScoringCriteria.project_id == project_id,
        )
    )
    criteria = result.scalar_one_or_none()
    if not criteria:
        raise HTTPException(status_code=404, detail="评分项不存在")
    await db.delete(criteria)
    return {"message": "评分项已删除"}
