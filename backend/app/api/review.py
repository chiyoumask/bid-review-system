"""
审核 API - 创建审核任务、查看结果、人工复核
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import (
    Project, ProjectDocument, ScoringCriteria, ReviewTask, ReviewResult
)
from app.schemas.project import (
    ReviewTaskCreate, ReviewTaskResponse, ReviewTaskDetail,
    ReviewResultResponse, ReviewResultUpdate,
)

router = APIRouter()


@router.get("/tasks", response_model=List[ReviewTaskResponse])
async def list_tasks(
    project_id: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List review tasks, optionally filtered by project."""
    query = select(ReviewTask)
    if project_id:
        query = query.where(ReviewTask.project_id == project_id)
    query = query.order_by(ReviewTask.created_at.desc())

    result = await db.execute(query)
    tasks = result.scalars().all()
    return [ReviewTaskResponse.model_validate(t) for t in tasks]


@router.post("/tasks", response_model=ReviewTaskResponse, status_code=201)
async def create_review_task(
    data: ReviewTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new review task (starts analysis in background)."""
    # Verify project and document exist
    project = await db.get(Project, data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    document = await db.get(ProjectDocument, data.bid_document_id)
    if not document or document.project_id != data.project_id:
        raise HTTPException(status_code=404, detail="投标文件不存在或不属于该项目")

    # Check scoring criteria exist
    criteria_result = await db.execute(
        select(ScoringCriteria).where(ScoringCriteria.project_id == data.project_id)
    )
    criteria_list = criteria_result.scalars().all()
    if not criteria_list:
        raise HTTPException(status_code=400, detail="请先配置评分标准")

    # Create task
    task = ReviewTask(
        project_id=data.project_id,
        bid_document_id=data.bid_document_id,
        bidder_name=data.bidder_name,
        status="pending",
        created_by=current_user.id,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # Trigger background analysis
    from app.tasks.document_tasks import analyze_bid_task
    import asyncio
    asyncio.create_task(analyze_bid_task(task.id))

    return ReviewTaskResponse.model_validate(task)


@router.get("/tasks/{task_id}", response_model=ReviewTaskDetail)
async def get_review_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get review task detail with all results."""
    result = await db.execute(
        select(ReviewTask)
        .options(selectinload(ReviewTask.results))
        .where(ReviewTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="审核任务不存在")

    return ReviewTaskDetail(
        **{k: getattr(task, k) for k in ReviewTaskResponse.model_fields},
        results=[ReviewResultResponse.model_validate(r) for r in task.results],
    )


@router.put("/results/{result_id}")
async def update_review_result(
    result_id: int,
    data: ReviewResultUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a review result (human review/override)."""
    result = await db.execute(
        select(ReviewResult).where(ReviewResult.id == result_id)
    )
    review_result = result.scalar_one_or_none()
    if not review_result:
        raise HTTPException(status_code=404, detail="审核结果不存在")

    review_result.reviewer_status = data.reviewer_status
    review_result.reviewer_score = data.reviewer_score
    review_result.reviewer_comment = data.reviewer_comment
    review_result.reviewed_by = current_user.id
    review_result.reviewed_at = datetime.utcnow()

    return {"message": "审核结果已更新"}


@router.post("/tasks/{task_id}/finalize")
async def finalize_review(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Finalize a review task - calculate final scores."""
    result = await db.execute(
        select(ReviewTask)
        .options(selectinload(ReviewTask.results))
        .where(ReviewTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="审核任务不存在")

    # Calculate final scores
    total_score = 0
    for r in task.results:
        if r.reviewer_status == "overridden" and r.reviewer_score is not None:
            total_score += r.reviewer_score
        elif r.ai_estimated_score is not None:
            total_score += r.ai_estimated_score

    task.estimated_score = total_score
    task.status = "completed"

    return {
        "message": "审核已完成",
        "total_score": total_score,
        "total_possible": task.total_possible_score,
    }
