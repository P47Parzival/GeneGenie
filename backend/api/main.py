"""
BioNexus India V2 — FastAPI Application

The main application entry point. Configures:
  - Lifespan handler (DB connection setup/teardown)
  - CORS middleware
  - Exception handlers
  - All route registrations (V1 + V2)
  - Static file mount for uploads/PDFs
  - Structured logging
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database import engine

# Import V1 routers
from api.routes.datasets import router as datasets_router
from api.routes.search import router as search_router
from api.routes.ingestion import router as ingestion_router
from api.routes.stats import router as stats_router

# Import V2 routers
from api.routes.auth import router as auth_router
from api.routes.institutions import router as institutions_router
from api.routes.access import router as access_router
from api.routes.feed_forms import router as feed_forms_router
from api.routes.audit import router as audit_router


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
    # Ensure upload directories exist
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.upload_dir, "documents").mkdir(parents=True, exist_ok=True)
    Path(settings.upload_dir, "feed_forms").mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("BioNexus India V2 — Starting up")
    logger.info(f"  Database: {settings.database_url.split('@')[-1]}")
    logger.info(f"  Redis: {settings.redis_url}")
    logger.info(f"  Log Level: {settings.log_level}")
    logger.info(f"  Uploads: {settings.upload_dir}")
    logger.info("=" * 60)

    yield

    logger.info("BioNexus India V2 — Shutting down")
    await engine.dispose()
    logger.info("Database connections closed")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="BioNexus India",
    description=(
        "India's first unified bioinformatics data infrastructure platform. "
        "V2: Access management, FeED compliance, and institutional onboarding. "
        "Discover datasets, request access, generate FeED-compliant forms."
    ),
    version="2.0.0",
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
# Static Files (for serving uploaded docs and generated PDFs)
# =============================================================================

# Create upload directory if it doesn't exist
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

app.mount(
    "/uploads",
    StaticFiles(directory=settings.upload_dir),
    name="uploads",
)


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
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

# V1 routes
app.include_router(datasets_router)
app.include_router(search_router)
app.include_router(ingestion_router)
app.include_router(stats_router)

# V2 routes
app.include_router(auth_router)
app.include_router(institutions_router)
app.include_router(access_router)
app.include_router(feed_forms_router)
app.include_router(audit_router)


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
        "version": "2.0.0",
        "status": "healthy",
        "description": (
            "India's first unified bioinformatics data infrastructure platform. "
            "V2: Access management & FeED compliance."
        ),
        "endpoints": {
            "v1": {
                "datasets": "/datasets",
                "search": "/search?q=",
                "ingest": "/ingest",
                "sources": "/sources",
                "stats": "/stats",
            },
            "v2": {
                "auth": "/auth/register, /auth/login, /auth/me",
                "institutions": "/institutions",
                "access_requests": "/access-requests",
                "feed_forms": "/feed-forms",
                "audit": "/audit/{resource_type}/{resource_id}",
            },
            "docs": "/docs",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
