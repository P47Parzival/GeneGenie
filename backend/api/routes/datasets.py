"""
BioNexus India V1 — Dataset Routes

GET /datasets       — paginated list with filters
GET /datasets/{id}  — full metadata for one dataset
"""

import math
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    DatasetResponse,
    DatasetListResponse,
    PaginationMeta,
)
from database import get_session
from database.models import Dataset

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Datasets"])


@router.get(
    "/datasets",
    response_model=DatasetListResponse,
    summary="List datasets with filters",
    description=(
        "Returns a paginated list of dataset metadata records. "
        "All filter parameters are optional and can be combined."
    ),
)
async def list_datasets(
    disease: str | None = Query(None, description="Filter by disease association (partial match)"),
    population: str | None = Query(None, description="Filter by population group (partial match)"),
    state: str | None = Query(None, description="Filter by state of collection (partial match)"),
    data_type: str | None = Query(None, description="Filter by data type: genomic, clinical, imaging, other"),
    source: str | None = Query(None, description="Filter by data source: indigenomes, ibdc, genomeindia, etc."),
    access_type: str | None = Query(None, description="Filter by access type: open, managed, controlled"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    session: AsyncSession = Depends(get_session),
):
    """List datasets with optional filters and pagination."""

    # Build base query
    query = select(Dataset)
    count_query = select(func.count()).select_from(Dataset)

    # Apply filters (case-insensitive partial match)
    if disease:
        query = query.where(Dataset.disease_association.ilike(f"%{disease}%"))
        count_query = count_query.where(Dataset.disease_association.ilike(f"%{disease}%"))

    if population:
        query = query.where(Dataset.population_group.ilike(f"%{population}%"))
        count_query = count_query.where(Dataset.population_group.ilike(f"%{population}%"))

    if state:
        query = query.where(Dataset.state_of_collection.ilike(f"%{state}%"))
        count_query = count_query.where(Dataset.state_of_collection.ilike(f"%{state}%"))

    if data_type:
        query = query.where(Dataset.data_type == data_type.lower())
        count_query = count_query.where(Dataset.data_type == data_type.lower())

    if source:
        query = query.where(Dataset.source == source.lower())
        count_query = count_query.where(Dataset.source == source.lower())

    if access_type:
        query = query.where(Dataset.access_type == access_type.lower())
        count_query = count_query.where(Dataset.access_type == access_type.lower())

    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * limit
    query = query.order_by(Dataset.date_ingested.desc()).offset(offset).limit(limit)

    # Execute
    result = await session.execute(query)
    datasets = result.scalars().all()

    return DatasetListResponse(
        data=[DatasetResponse.model_validate(d) for d in datasets],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=math.ceil(total / limit) if total > 0 else 0,
        ),
    )


@router.get(
    "/datasets/{dataset_id}",
    response_model=DatasetResponse,
    summary="Get dataset by ID",
    description="Returns the full metadata for a single dataset by its UUID.",
)
async def get_dataset(
    dataset_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single dataset by its ID."""

    result = await session.execute(
        select(Dataset).where(Dataset.dataset_id == dataset_id)
    )
    dataset = result.scalar_one_or_none()

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with ID '{dataset_id}' not found",
        )

    return DatasetResponse.model_validate(dataset)
