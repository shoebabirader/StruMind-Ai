"""
Core configuration settings for StruMind Backend
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "StruMind"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./strumind.db", env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    
    # Security
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000", 
            "https://app.strumind.com",
            "https://work-2-tgaufxkwcjeifuoc.prod-runtime.all-hands.dev"
        ],
        env="ALLOWED_ORIGINS"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=[
            "localhost", 
            "127.0.0.1", 
            "api.strumind.com",
            "work-1-tgaufxkwcjeifuoc.prod-runtime.all-hands.dev"
        ],
        env="ALLOWED_HOSTS"
    )
    
    # File Storage
    UPLOAD_DIR: str = Field(default="uploads", env="UPLOAD_DIR")
    MAX_FILE_SIZE: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 100MB
    
    # AWS S3 (optional)
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: Optional[str] = Field(default=None, env="AWS_REGION")
    S3_BUCKET: Optional[str] = Field(default=None, env="S3_BUCKET")
    
    # Email (optional)
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: Optional[int] = Field(default=587, env="SMTP_PORT")
    SMTP_USERNAME: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    # Computational limits
    MAX_NODES: int = Field(default=100000, env="MAX_NODES")
    MAX_ELEMENTS: int = Field(default=100000, env="MAX_ELEMENTS")
    MAX_LOAD_CASES: int = Field(default=1000, env="MAX_LOAD_CASES")
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()