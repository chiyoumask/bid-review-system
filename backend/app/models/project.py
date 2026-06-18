"""
项目、文档、评分标准、审核任务、审核结果模型
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Project(Base):
    """审核项目 - 每个招投标项目对应一条"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    bid_number = Column(String(100), nullable=True)  # 招标编号
    status = Column(String(20), default="draft")  # draft, analyzing, completed, archived
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = relationship("ProjectDocument", back_populates="project", cascade="all, delete-orphan")
    scoring_criteria = relationship("ScoringCriteria", back_populates="project", cascade="all, delete-orphan")
    review_tasks = relationship("ReviewTask", back_populates="project", cascade="all, delete-orphan")


class ProjectDocument(Base):
    """项目关联的文档 - 评分标准文件、投标文件等"""
    __tablename__ = "project_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    doc_type = Column(String(30), nullable=False)  # scoring_criteria, tender_doc, supplementary
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=True)  # bytes
    page_count = Column(Integer, nullable=True)
    parsed_text = Column(Text, nullable=True)  # 解析后的纯文本
    parsed_json = Column(JSON, nullable=True)  # 结构化提取结果
    status = Column(String(20), default="uploaded")  # uploaded, parsing, parsed, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="documents")


class ScoringCriteria(Base):
    """解析后的评分标准 - 从评分标准文件中提取"""
    __tablename__ = "scoring_criteria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    category = Column(String(50), nullable=False)  # 资质、技术、商务、价格 等大类
    item_name = Column(String(200), nullable=False)  # 评分项名称
    max_score = Column(Float, nullable=False)  # 该项满分
    description = Column(Text, nullable=True)  # 评分细则描述
    evaluation_criteria = Column(Text, nullable=True)  # 具体评分标准（AI解析的）
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="scoring_criteria")


class ReviewTask(Base):
    """审核任务 - 一份投标文件的审核"""
    __tablename__ = "review_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    bid_document_id = Column(Integer, ForeignKey("project_documents.id"), nullable=False)
    bidder_name = Column(String(200), nullable=True)  # 投标单位名称
    status = Column(String(20), default="pending")  # pending, analyzing, completed, error
    total_possible_score = Column(Float, nullable=True)  # 满分
    estimated_score = Column(Float, nullable=True)  # AI预估得分
    risk_count_high = Column(Integer, default=0)
    risk_count_medium = Column(Integer, default=0)
    risk_count_low = Column(Integer, default=0)
    summary = Column(Text, nullable=True)  # AI生成的总结
    error_message = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="review_tasks")
    bid_document = relationship("ProjectDocument")
    results = relationship("ReviewResult", back_populates="task", cascade="all, delete-orphan")


class ReviewResult(Base):
    """单项评分结果 - 对应一个评分标准项的审核结果"""
    __tablename__ = "review_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("review_tasks.id"), nullable=False)
    criteria_id = Column(Integer, ForeignKey("scoring_criteria.id"), nullable=False)
    category = Column(String(50), nullable=False)
    item_name = Column(String(200), nullable=False)
    max_score = Column(Float, nullable=False)
    ai_estimated_score = Column(Float, nullable=True)  # AI预估得分
    ai_analysis = Column(Text, nullable=True)  # AI分析说明
    risk_level = Column(String(10), nullable=True)  # high, medium, low, none
    risk_description = Column(Text, nullable=True)  # 风险描述
    bid_content_excerpt = Column(Text, nullable=True)  # 标书中对应的原文摘录
    evidence_locations = Column(JSON, nullable=True)  # 证据位置（页码等）
    # 人工复核字段
    reviewer_status = Column(String(20), default="pending")  # pending, confirmed, overridden, ignored
    reviewer_score = Column(Float, nullable=True)  # 人工调整得分
    reviewer_comment = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("ReviewTask", back_populates="results")
    criteria = relationship("ScoringCriteria")
