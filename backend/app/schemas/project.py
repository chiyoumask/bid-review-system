"""
项目、文档、评分标准、审核相关 Schema
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# --- Project ---

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    bid_number: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    bid_number: Optional[str] = None
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    task_count: int = 0

    model_config = {"from_attributes": True}


class ProjectDetail(ProjectResponse):
    documents: List["DocumentResponse"] = []
    scoring_criteria: List["ScoringCriteriaResponse"] = []


# --- Document ---

class DocumentResponse(BaseModel):
    id: int
    project_id: int
    doc_type: str
    filename: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Scoring Criteria ---

class ScoringCriteriaCreate(BaseModel):
    category: str
    item_name: str
    max_score: float
    description: Optional[str] = None
    evaluation_criteria: Optional[str] = None
    sort_order: int = 0


class ScoringCriteriaResponse(BaseModel):
    id: int
    project_id: int
    category: str
    item_name: str
    max_score: float
    description: Optional[str] = None
    evaluation_criteria: Optional[str] = None
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Review Task ---

class ReviewTaskCreate(BaseModel):
    project_id: int
    bid_document_id: int
    bidder_name: Optional[str] = None


class ReviewTaskResponse(BaseModel):
    id: int
    project_id: int
    bid_document_id: int
    bidder_name: Optional[str] = None
    status: str
    total_possible_score: Optional[float] = None
    estimated_score: Optional[float] = None
    risk_count_high: int = 0
    risk_count_medium: int = 0
    risk_count_low: int = 0
    summary: Optional[str] = None
    error_message: Optional[str] = None
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewTaskDetail(ReviewTaskResponse):
    results: List["ReviewResultResponse"] = []


# --- Review Result ---

class ReviewResultResponse(BaseModel):
    id: int
    task_id: int
    criteria_id: int
    category: str
    item_name: str
    max_score: float
    ai_estimated_score: Optional[float] = None
    ai_analysis: Optional[str] = None
    risk_level: Optional[str] = None
    risk_description: Optional[str] = None
    bid_content_excerpt: Optional[str] = None
    evidence_locations: Optional[dict] = None
    reviewer_status: str = "pending"
    reviewer_score: Optional[float] = None
    reviewer_comment: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewResultUpdate(BaseModel):
    reviewer_status: str  # confirmed, overridden, ignored
    reviewer_score: Optional[float] = None
    reviewer_comment: Optional[str] = None


# --- LLM Provider Settings ---

class LLMProviderConfig(BaseModel):
    id: Optional[int] = None
    name: str
    provider_type: str  # openai, deepseek, qwen, custom
    api_key: str
    base_url: str
    model_name: str
    is_active: bool = True
    priority: int = 0  # lower = higher priority


class LLMProviderResponse(BaseModel):
    id: Optional[int] = None
    name: str
    provider_type: str
    base_url: str
    model_name: str
    is_active: bool
    priority: int
    # api_key is never returned

    model_config = {"from_attributes": True}
