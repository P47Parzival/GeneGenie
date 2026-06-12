"""
BioNexus India V1 — Ingestion Routes

POST /ingest   — trigger ingestion pipeline for a specific source
GET  /sources  — list all available sources and their last ingestion timestamp
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    IngestRequest,
    IngestResponse,
    SourceInfo,
    SourcesResponse,
    ErrorResponse,
)
from database import get_session
from database.models import Dataset, IngestionLog
from ingestion.pipeline import IngestionPipeline, ADAPTER_REGISTRY

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ingestion"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Unknown source"},
    },
    summary="Trigger data ingestion",
    description=(
        "Triggers the ingestion pipeline for the specified data source. "
        "The pipeline will fetch metadata from the source, standardize it, "
        "and upsert it into the database."
    ),
)
async def trigger_ingestion(request: IngestRequest):
    """
    Trigger ingestion for a specific source.

    This runs synchronously — the response is returned after the
    pipeline completes. For production, this should be made async
    with a task queue (V2 scope).
    """
    source = request.source.lower()

    # Validate source
    if source not in ADAPTER_REGISTRY:
        available = ", ".join(ADAPTER_REGISTRY.keys())
        return IngestResponse(
            source=source,
            status="failure",
            error=f"Unknown source: '{source}'. Available: {available}",
        )

    logger.info(f"Ingestion triggered via API for source: {source}")

    # Run the pipeline
    pipeline = IngestionPipeline()
    result = await pipeline.run(source)

    return IngestResponse(
        source=result["source"],
        status=result["status"],
        records_fetched=result.get("records_fetched"),
        records_ingested=result.get("records_ingested"),
        records_failed=result.get("records_failed"),
        error=result.get("error"),
        started_at=result.get("started_at"),
        completed_at=result.get("completed_at"),
        duration_seconds=result.get("duration_seconds"),
    )


@router.get(
    "/sources",
    response_model=SourcesResponse,
    summary="List all data sources",
    description=(
        "Returns all available data sources with their last ingestion "
        "timestamp, status, and total dataset count."
    ),
)
async def list_sources(
    session: AsyncSession = Depends(get_session),
):
    """List all registered data sources with ingestion metadata."""

    sources = []

    for source_name in ADAPTER_REGISTRY.keys():
        # Get last ingestion log for this source
        log_result = await session.execute(
            select(IngestionLog)
            .where(IngestionLog.source == source_name)
            .order_by(desc(IngestionLog.completed_at))
            .limit(1)
        )
        last_log = log_result.scalar_one_or_none()

        # Get total datasets from this source
        count_result = await session.execute(
            select(func.count())
            .select_from(Dataset)
            .where(Dataset.source == source_name)
        )
        total_datasets = count_result.scalar_one()

        sources.append(
            SourceInfo(
                name=source_name,
                last_ingestion_at=(
                    last_log.completed_at if last_log else None
                ),
                last_ingestion_status=(
                    last_log.status if last_log else None
                ),
                total_datasets=total_datasets,
            )
        )

    return SourcesResponse(sources=sources)
