"""
BioNexus India V1 — Stats Route

GET /stats — aggregate statistics about the dataset warehouse
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import StatsResponse, StatsBreakdown
from database import get_session
from database.models import Dataset

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Statistics"])


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Dataset warehouse statistics",
    description=(
        "Returns aggregate statistics: total datasets, and breakdowns "
        "by source, data type, state of collection, population group, "
        "and access type."
    ),
)
async def get_stats(
    session: AsyncSession = Depends(get_session),
):
    """Get aggregate statistics about the dataset warehouse."""

    # Total datasets
    total_result = await session.execute(
        select(func.count()).select_from(Dataset)
    )
    total_datasets = total_result.scalar_one()

    # Breakdown by source
    by_source = await _get_breakdown(session, Dataset.source)

    # Breakdown by data type
    by_data_type = await _get_breakdown(session, Dataset.data_type)

    # Breakdown by state
    by_state = await _get_breakdown(session, Dataset.state_of_collection)

    # Breakdown by population
    by_population = await _get_breakdown(session, Dataset.population_group)

    # Breakdown by access type
    by_access_type = await _get_breakdown(session, Dataset.access_type)

    return StatsResponse(
        total_datasets=total_datasets,
        by_source=by_source,
        by_data_type=by_data_type,
        by_state=by_state,
        by_population=by_population,
        by_access_type=by_access_type,
    )


async def _get_breakdown(session: AsyncSession, column) -> list[StatsBreakdown]:
    """
    Get count breakdown for a specific column.

    Groups by the column value and returns (category, count) pairs,
    sorted by count descending. NULL values are grouped as "Unknown".
    """
    result = await session.execute(
        select(
            func.coalesce(column, "Unknown").label("category"),
            func.count().label("count"),
        )
        .select_from(Dataset)
        .group_by(func.coalesce(column, "Unknown"))
        .order_by(func.count().desc())
    )

    return [
        StatsBreakdown(category=row.category, count=row.count)
        for row in result.all()
    ]
