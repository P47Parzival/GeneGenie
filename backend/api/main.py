"""
BioNexus India V1 — FastAPI Application

The main application entry point. Configures:
  - Lifespan handler (DB connection setup/teardown)
  - CORS middleware
  - Exception handlers
  - All route registrations
  - Structured logging

Run with:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import engine

# Import routers
from api.routes.datasets import router as datasets_router
from api.routes.search import router as search_router
from api.routes.ingestion import router as ingestion_router
from api.routes.stats import router as stats_router


# =============================================================================
# Logging Configuration
# =============================================================================

def setup_logging():
    """Configure structured logging for the application."""
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — runs on startup and shutdown."""
    logger.info("=" * 60)
    logger.info("BioNexus India V1 — Starting up")
    logger.info(f"  Database: {settings.database_url.split('@')[-1]}")
    logger.info(f"  Log Level: {settings.log_level}")
    logger.info("=" * 60)

    yield  # App runs here

    # Shutdown
    logger.info("BioNexus India V1 — Shutting down")
    await engine.dispose()
    logger.info("Database connections closed")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="BioNexus India",
    description=(
        "India's first unified bioinformatics metadata warehouse. "
        "Discover and search standardized metadata from Indian biological "
        "data sources including IndiGenomes, IBDC, GenomeIndia, and more."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# =============================================================================
# Middleware
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError as 400 Bad Request."""
    return JSONResponse(
        status_code=400,
        content={
            "error": "Bad Request",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler."""
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred. Please try again later.",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# =============================================================================
# Route Registration
# =============================================================================

app.include_router(datasets_router)
app.include_router(search_router)
app.include_router(ingestion_router)
app.include_router(stats_router)


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get(
    "/",
    tags=["Health"],
    summary="API root / health check",
)
async def root():
    """Health check endpoint — confirms the API is running."""
    return {
        "service": "BioNexus India",
        "version": "1.0.0",
        "status": "healthy",
        "description": (
            "India's first unified bioinformatics metadata warehouse. "
            "Visit /docs for the interactive API documentation."
        ),
        "endpoints": {
            "datasets": "/datasets",
            "search": "/search?q=",
            "ingest": "/ingest",
            "sources": "/sources",
            "stats": "/stats",
            "docs": "/docs",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
