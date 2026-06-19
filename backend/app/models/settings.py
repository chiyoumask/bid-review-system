"""
系统设置相关模型
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.core.database import Base


class LLMProvider(Base):
    """User-scoped LLM provider configuration."""

    __tablename__ = "llm_providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    provider_type = Column(String(30), nullable=False)
    api_key = Column(String(500), nullable=False)
    base_url = Column(String(500), nullable=False)
    model_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
