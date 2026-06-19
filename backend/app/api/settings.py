"""
系统设置 API - LLM 渠道管理、系统配置
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.settings import LLMProvider
from app.schemas.project import LLMProviderConfig, LLMProviderResponse

router = APIRouter()


class DashboardStats(BaseModel):
    total_projects: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    high_risk_count: int = 0


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics."""
    from app.models.project import Project, ReviewTask

    project_count = await db.execute(
        select(Project).where(Project.created_by == current_user.id)
    )
    projects = project_count.scalars().all()
    project_ids = [p.id for p in projects]

    if project_ids:
        task_result = await db.execute(
            select(ReviewTask).where(ReviewTask.project_id.in_(project_ids))
        )
        tasks = task_result.scalars().all()
    else:
        tasks = []

    return DashboardStats(
        total_projects=len(projects),
        total_tasks=len(tasks),
        completed_tasks=len([t for t in tasks if t.status == "completed"]),
        high_risk_count=sum(t.risk_count_high for t in tasks),
    )


# --- LLM Provider Management ---

@router.get("/llm-providers", response_model=List[LLMProviderResponse])
async def list_llm_providers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List configured LLM providers."""
    result = await db.execute(
        select(LLMProvider)
        .where(LLMProvider.created_by == current_user.id)
        .order_by(LLMProvider.priority.asc(), LLMProvider.id.asc())
    )
    return [LLMProviderResponse.model_validate(p) for p in result.scalars().all()]


@router.post("/llm-providers", response_model=LLMProviderResponse, status_code=201)
async def add_llm_provider(
    config: LLMProviderConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new LLM provider configuration."""
    if config.provider_type not in {"deepseek", "qwen", "openai", "custom"}:
        raise HTTPException(status_code=400, detail="不支持的渠道类型")
    if not config.name.strip() or not config.api_key.strip() or not config.base_url.strip() or not config.model_name.strip():
        raise HTTPException(status_code=400, detail="渠道名称、API Key、Base URL 和模型名称不能为空")

    provider = LLMProvider(
        name=config.name.strip(),
        provider_type=config.provider_type,
        api_key=config.api_key.strip(),
        base_url=config.base_url.strip().rstrip("/"),
        model_name=config.model_name.strip(),
        is_active=config.is_active,
        priority=config.priority,
        created_by=current_user.id,
    )
    db.add(provider)
    await db.flush()
    await db.refresh(provider)
    return LLMProviderResponse.model_validate(provider)


@router.delete("/llm-providers/{provider_id}")
async def delete_llm_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an LLM provider configuration."""
    result = await db.execute(
        select(LLMProvider).where(
            LLMProvider.id == provider_id,
            LLMProvider.created_by == current_user.id,
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="渠道不存在")
    await db.delete(provider)
    return {"message": "已删除"}


@router.post("/llm-providers/{provider_id}/test")
async def test_llm_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test an LLM provider connection."""
    result = await db.execute(
        select(LLMProvider).where(
            LLMProvider.id == provider_id,
            LLMProvider.created_by == current_user.id,
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="渠道不存在")

    from app.services.llm_client import LLMClient
    client = LLMClient(
        api_key=provider.api_key,
        base_url=provider.base_url,
        model=provider.model_name,
        timeout=15,
    )
    try:
        response = await client.chat([
            {"role": "user", "content": "请回复'连接成功'四个字。"}
        ])
        await client.close()
        return {"success": True, "response": response}
    except Exception as e:
        await client.close()
        return {"success": False, "error": str(e)}
