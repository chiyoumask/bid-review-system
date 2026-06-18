"""
应用配置 - 从环境变量加载
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "招投标文件智能审核系统"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-a-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bid_review"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]

    # File storage
    BASE_DIR: str = str(Path(__file__).resolve().parent.parent.parent)
    UPLOAD_DIR: str = ""
    OUTPUT_DIR: str = ""

    # LLM default settings
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"
    LLM_TIMEOUT: int = 120

    # Max file size (MB)
    MAX_FILE_SIZE_MB: int = 50

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.UPLOAD_DIR:
            self.UPLOAD_DIR = os.path.join(self.BASE_DIR, "data", "uploads")
        if not self.OUTPUT_DIR:
            self.OUTPUT_DIR = os.path.join(self.BASE_DIR, "data", "outputs")
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)


settings = Settings()
