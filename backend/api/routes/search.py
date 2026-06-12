"""
BioNexus India V2 — Search Route

GET /search?q=  — Full-text search across all metadata fields
                  with optional filters

V2 update: Unauthenticated returns limited metadata;
authenticated returns full metadata including contacts.
"""

import math
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    DatasetResponse,
    DatasetPublicResponse,
    SearchResponse,
    PaginationMeta,
)
from database import get_session
from database.models import Dataset, User
from services.auth_service import get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Search"])


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Full-text search across datasets",
    description=(
        "Search across all dataset metadata fields using PostgreSQL full-text search. "
        "Unauthenticated: limited metadata. Authenticated: full metadata."
    ),
)
async def search_datasets(
    q: str = Query(
        ...,
        min_length=1,
        max_length=500,
        description="Search query",
    ),
    disease: str | None = Query(None, description="Filter by disease association"),
    population: str | None = Query(None, description="Filter by population group"),
    state: str | None = Query(None, description="Filter by state of collection"),
    data_type: str | None = Query(None, description="Filter by data type"),
    source: str | None = Query(None, description="Filter by data source"),
    access_type: str | None = Query(None, description="Filter by access type"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    user: Optional[User] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
):
    """Full-text search with optional filters and role-based metadata."""

    authenticated = user is not None

    # Convert search query to PostgreSQL tsquery
    ts_query = func.plainto_tsquery("english", q)

    # Base query with full-text search match
    query = (
        select(
            Dataset,
            func.ts_rank(Dataset.search_vector, ts_query).label("rank"),
        )
        .where(Dataset.search_vector.op("@@")(ts_query))
    )

    count_query = (
        select(func.count())
        .select_from(Dataset)
        .where(Dataset.search_vector.op("@@")(ts_query))
    )

    # Track applied filters
    filters_applied = {"q": q}

    # Apply additional filters
    if disease:
        query = query.where(Dataset.disease_association.ilike(f"%{disease}%"))
        count_query = count_query.where(Dataset.disease_association.ilike(f"%{disease}%"))
        filters_applied["disease"] = disease

    if population:
        query = query.where(Dataset.population_group.ilike(f"%{population}%"))
        count_query = count_query.where(Dataset.population_group.ilike(f"%{population}%"))
        filters_applied["population"] = population

    if state:
        query = query.where(Dataset.state_of_collection.ilike(f"%{state}%"))
        count_query = count_query.where(Dataset.state_of_collection.ilike(f"%{state}%"))
        filters_applied["state"] = state

    if data_type:
        query = query.where(Dataset.data_type == data_type.lower())
        count_query = count_query.where(Dataset.data_type == data_type.lower())
        filters_applied["data_type"] = data_type

    if source:
        query = query.where(Dataset.source == source.lower())
        count_query = count_query.where(Dataset.source == source.lower())
        filters_applied["source"] = source

    if access_type:
        query = query.where(Dataset.access_type == access_type.lower())
        count_query = count_query.where(Dataset.access_type == access_type.lower())
        filters_applied["access_type"] = access_type

    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination and ordering
    offset = (page - 1) * limit
    query = query.order_by(desc("rank")).offset(offset).limit(limit)

    # Execute
    result = await session.execute(query)
    rows = result.all()

    # Serialize based on auth status
    datasets = []
    for row in rows:
        ds = row[0]
        if authenticated:
            datasets.append(DatasetResponse.model_validate(ds))
        else:
            datasets.append(DatasetPublicResponse.model_validate(ds))

    logger.info(
        f"Search: q='{q}', auth={authenticated}, "
        f"results={total}, page={page}"
    )

    return SearchResponse(
        query=q,
        data=datasets,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=math.ceil(total / limit) if total > 0 else 0,
        ),
        filters_applied=filters_applied,
    )
