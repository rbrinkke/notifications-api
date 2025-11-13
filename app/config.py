"""
Configuration management using Pydantic Settings.
Reads from environment variables and .env file.
"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Notifications API"

    # Database
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    # Internal Service Auth
    SERVICE_TOKEN: str

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # Email API (optional)
    EMAIL_API_URL: Optional[str] = None
    EMAIL_API_KEY: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"

    # CORS
    CORS_ORIGINS: str = "*"  # Comma-separated list of origins or "*"

    # API Documentation
    ENABLE_DOCS: bool = True

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
