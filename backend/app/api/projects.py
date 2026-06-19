"""
项目管理 API - 项目CRUD、文件上传、评分标准管理
"""
import os
import uuid
from typing import List

import aiofiles
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


def _project_response(project: Project, document_count: int = 0, task_count: int = 0) -> ProjectResponse:
    """Build a project response with calculated counters."""
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        bid_number=project.bid_number,
        status=project.status,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        document_count=document_count,
        task_count=task_count,
    )


async def _get_owned_project(project_id: int, db: AsyncSession, current_user: User) -> Project:
    """Load a project and ensure it belongs to the current user."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此项目")
    return project


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
        response.append(_project_response(
            p,
            document_count=doc_count.scalar() or 0,
            task_count=task_count.scalar() or 0,
        ))
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
    return _project_response(project, document_count=0, task_count=0)


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get project detail with documents and scoring criteria."""
    project = await _get_owned_project(project_id, db, current_user)

    result = await db.execute(
        select(Project)
        .options(selectinload(Project.documents), selectinload(Project.scoring_criteria))
        .where(Project.id == project_id)
    )
    project = result.scalar_one()

    doc_count = await db.execute(
        select(func.count(ProjectDocument.id)).where(ProjectDocument.project_id == project_id)
    )
    task_count = await db.execute(
        select(func.count(ReviewTask.id)).where(ReviewTask.project_id == project_id)
    )

    return ProjectDetail(
        **_project_response(
            project,
            document_count=doc_count.scalar() or 0,
            task_count=task_count.scalar() or 0,
        ).model_dump(),
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
    project = await _get_owned_project(project_id, db, current_user)

    await db.delete(project)
    return {"message": "项目已删除"}


# --- Document Upload ---

@router.post("/{project_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    project_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = Form("tender_doc"),  # scoring_criteria, tender_doc, supplementary
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a document to a project."""
    await _get_owned_project(project_id, db, current_user)

    if doc_type not in {"scoring_criteria", "tender_doc", "supplementary"}:
        raise HTTPException(status_code=400, detail=f"不支持的文档类型: {doc_type}")

    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".txt"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")

    # Save file
    project_dir = os.path.join(settings.UPLOAD_DIR, str(project_id))
    os.makedirs(project_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{ext}"
    file_path = os.path.join(project_dir, safe_filename)

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    file_size = 0
    async with aiofiles.open(file_path, "wb") as out_file:
        while chunk := await file.read(1024 * 1024):
            file_size += len(chunk)
            if file_size > max_bytes:
                await out_file.close()
                try:
                    os.remove(file_path)
                except FileNotFoundError:
                    pass
                raise HTTPException(
                    status_code=413,
                    detail=f"文件超过大小限制: {settings.MAX_FILE_SIZE_MB}MB",
                )
            await out_file.write(chunk)

    # Create document record
    doc = ProjectDocument(
        project_id=project_id,
        doc_type=doc_type,
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        status="uploaded",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    await db.commit()

    # Trigger background parsing
    from app.tasks.document_tasks import parse_document_task
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
    await _get_owned_project(project_id, db, current_user)
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
    await _get_owned_project(project_id, db, current_user)
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
    await _get_owned_project(project_id, db, current_user)
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
    await _get_owned_project(project_id, db, current_user)
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
