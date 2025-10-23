from pydantic_settings import BaseSettings
from typing import List


class AppSettings(BaseSettings):
    """Manages application settings using environment variables."""

    DATABASE_URL: str = "sqlite:///./dispatch.db"
    HPC_USER_SERVICE_URL: str = "http://127.0.0.1:8090/api/v1"
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
    ]
    MOCK_AUTH_ENABLED: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = AppSettings()
