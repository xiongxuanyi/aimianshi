"""全局配置：通过环境变量 / .env 注入；无密钥时自动使用 FakeLLM。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    # ---- 大模型 ----
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""          # 留空 -> FakeLLM 离线模式
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.6
    llm_timeout: float = 60.0

    # ---- 上传 ----
    upload_dir: str = str(BACKEND_DIR / "uploads")
    max_upload_mb: int = 5
    allowed_ext: List[str] = [".pdf", ".docx", ".doc"]

    # ---- 会话 ----
    session_ttl_minutes: int = 60

    # ---- 安全 ----
    secret_key: str = "interview-training-secret-change-me"

    # ---- 服务 ----
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
os.makedirs(settings.upload_dir, exist_ok=True)
