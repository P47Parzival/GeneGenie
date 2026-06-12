"""
BioNexus India V1 — API Schemas (Pydantic Models)

Defines all request/response models for the API.
Every response includes consistent metadata: pagination, timestamps,
and source attribution.
"""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Pagination
# =============================================================================


class PaginationMeta(BaseModel):
    """Pagination metadata included in every list response."""

    page: int = Field(description="Current page number (1-indexed)")
    limit: int = Field(description="Items per page")
    total: int = Field(description="Total matching records")
    total_pages: int = Field(description="Total pages available")


# =============================================================================
# Dataset
# =============================================================================


class DatasetResponse(BaseModel):
    """Full metadata for a single dataset."""

    dataset_id: uuid.UUID
    name: str
    source: str
    institution_name: str | None = None
    state_of_collection: str | None = None
    population_group: str | None = None
    data_type: str | None = None
    disease_association: str | None = None
    sample_size: int | None = None
    collection_date: date | None = None
    access_type: str | None = None
    source_url: str | None = None
    ethics_approval_number: str | None = None
    contact_researcher: str | None = None
    license_type: str | None = None
    doi: str | None = None
    raw_checksum: str | None = None
    date_ingested: datetime | None = None

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    """Paginated list of datasets with metadata."""

    data: list[DatasetResponse]
    pagination: PaginationMeta
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Search
# =============================================================================


class SearchResponse(BaseModel):
    """Search results with query echo and pagination."""

    query: str = Field(description="The search query that was executed")
    data: list[DatasetResponse]
    pagination: PaginationMeta
    filters_applied: dict[str, str] = Field(
        default_factory=dict,
        description="Active filters applied to the search",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Ingestion
# =============================================================================


class IngestRequest(BaseModel):
    """Request body for triggering ingestion."""

    source: str = Field(
        description="Source to ingest from (e.g., 'indigenomes', 'ibdc', 'genomeindia')"
    )


class IngestResponse(BaseModel):
    """Response from an ingestion pipeline run."""

    source: str
    status: str = Field(description="Status: success, partial_failure, failure")
    records_fetched: int | None = None
    records_ingested: int | None = None
    records_failed: int | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Sources
# =============================================================================


class SourceInfo(BaseModel):
    """Information about a data source."""

    name: str = Field(description="Source identifier")
    last_ingestion_at: datetime | None = Field(
        default=None, description="Timestamp of last successful ingestion"
    )
    last_ingestion_status: str | None = Field(
        default=None, description="Status of last ingestion run"
    )
    total_datasets: int = Field(
        default=0, description="Total datasets from this source"
    )


class SourcesResponse(BaseModel):
    """List of all available data sources."""

    sources: list[SourceInfo]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Stats
# =============================================================================


class StatsBreakdown(BaseModel):
    """Breakdown of counts by a category."""

    category: str
    count: int


class StatsResponse(BaseModel):
    """Aggregate statistics about the dataset warehouse."""

    total_datasets: int
    by_source: list[StatsBreakdown]
    by_data_type: list[StatsBreakdown]
    by_state: list[StatsBreakdown]
    by_population: list[StatsBreakdown]
    by_access_type: list[StatsBreakdown]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Error
# =============================================================================


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
