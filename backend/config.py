"""
BioNexus India V1 — Centralized Configuration

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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


# Singleton settings instance — import this everywhere
settings = Settings()
