"""
BioNexus India V2 — Centralized Configuration

All application settings are loaded from environment variables (or .env file).
This is the single source of truth for configuration across all modules.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Database ---
    database_url: str = Field(
        default="postgresql+asyncpg://bionexus:bionexus_secret@localhost:5432/bionexus",
        description="Async database connection URL (asyncpg driver)",
    )
    sync_database_url: str = Field(
        default="postgresql://bionexus:bionexus_secret@localhost:5432/bionexus",
        description="Sync database connection URL (for Alembic migrations)",
    )

    # --- API Server ---
    api_host: str = Field(default="0.0.0.0", description="API server bind host")
    api_port: int = Field(default=8000, description="API server bind port")
    log_level: str = Field(default="INFO", description="Logging level")

    # --- Ingestion ---
    ingestion_timeout: int = Field(
        default=30, description="HTTP request timeout in seconds"
    )
    ingestion_max_retries: int = Field(
        default=3, description="Max retries for failed HTTP requests"
    )
    ingestion_backoff_base: float = Field(
        default=1.0, description="Base delay for exponential backoff (seconds)"
    )

    # --- Raw Data Storage ---
    raw_data_dir: str = Field(
        default="data/raw",
        description="Directory to store raw fetched responses for debugging",
    )

    # --- V2: JWT Authentication ---
    jwt_secret_key: str = Field(
        default="bionexus-dev-secret-key-change-in-production-immediately",
        description="Secret key for JWT token signing (CHANGE IN PRODUCTION)",
    )
    jwt_algorithm: str = Field(
        default="HS256", description="JWT signing algorithm"
    )
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiry in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiry in days"
    )

    # --- V2: Redis (Celery broker) ---
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for Celery task queue",
    )

    # --- V2: Email / SMTP ---
    smtp_host: str = Field(default="", description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    smtp_from_email: str = Field(
        default="noreply@bionexus.in", description="From address for emails"
    )
    smtp_from_name: str = Field(
        default="BioNexus India", description="From display name"
    )
    smtp_use_tls: bool = Field(default=True, description="Use TLS for SMTP")

    # --- V2: File Uploads ---
    upload_dir: str = Field(
        default="data/uploads",
        description="Directory for file uploads and generated PDFs",
    )
    max_upload_size_mb: int = Field(
        default=10, description="Maximum upload file size in MB"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


# Singleton settings instance — import this everywhere
settings = Settings()
