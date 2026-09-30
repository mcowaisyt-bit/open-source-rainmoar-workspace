from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "RainMoal Workspace"
    APP_ENV: str = "development"  # development | production
    SECRET_KEY: str = "dev-secret-key-change-in-production-please-use-long-random-string"
    DATABASE_URL: str = "sqlite:////tmp/ai_command_center.db"
    
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    CREDENTIAL_ENCRYPTION_KEY: str = "dev-encryption-key-32bytes!!"
    
    OPENAI_API_KEY: Optional[str] = None
    XAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/integrations/google/callback"
    
    # CORS — in production set to your desktop app origins / domain
    FRONTEND_URL: str = "http://localhost:5173"
    # Comma-separated extra origins, e.g. https://app.example.com,tauri://localhost
    CORS_ORIGINS: str = ""
    
    # Public API base URL (for docs / client config reference)
    PUBLIC_API_URL: str = "http://localhost:8000"
    
    class Config:
        env_file = str(ENV_FILE) if ENV_FILE.exists() else ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def cors_origin_list(self) -> List[str]:
        origins = [
            self.FRONTEND_URL,
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "tauri://localhost",
            "http://tauri.localhost",
            "https://tauri.localhost",
        ]
        if self.CORS_ORIGINS:
            origins.extend([o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()])
        # Deduplicate
        return list(dict.fromkeys(origins))


@lru_cache()
def get_settings() -> Settings:
    return Settings()
