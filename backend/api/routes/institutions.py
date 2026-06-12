"""
BioNexus India V2 — Institution Routes

POST /institutions/register    — institution submits profile
POST /institutions/verify      — admin verifies institution
GET  /institutions             — list all verified institutions
GET  /institutions/{id}        — institution profile and datasets
PUT  /institutions/{id}        — institution updates their profile
"""

import logging
import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    InstitutionRegisterRequest,
    InstitutionUpdateRequest,
    InstitutionVerifyRequest,
    InstitutionResponse,
    InstitutionListResponse,
    PaginationMeta,
    ErrorResponse,
)
from database import get_session
from database.models import Institution, Dataset, User
from services.auth_service import get_current_user, require_role
from services.audit_service import audit_service
from services.notification_service import notification_service, NotificationEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/institutions", tags=["Institutions"])

VALID_TYPES = {"government", "private", "academic"}
VALID_FUNDING = {"DBT", "ICMR", "DST", "state", "private"}


def _build_response(inst: Institution, dataset_count: int = 0) -> InstitutionResponse:
    """Build institution response with dataset count."""
    return InstitutionResponse(
        id=inst.id,
        institution_name=inst.institution_name,
        institution_type=inst.institution_type,
        state=inst.state,
        nodal_officer_name=inst.nodal_officer_name,
        nodal_officer_email=inst.nodal_officer_email,
        nodal_officer_phone=inst.nodal_officer_phone,
        funding_source=inst.funding_source,
        ibdc_registration_number=inst.ibdc_registration_number,
        is_verified=inst.is_verified,
        verified_at=inst.verified_at,
        created_at=inst.created_at,
        dataset_count=dataset_count,
    )


@router.post(
    "/register",
    response_model=InstitutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new institution",
)
async def register_institution(
    body: InstitutionRegisterRequest,
    request: Request,
    user: User = Depends(require_role("institution", "admin")),
    session: AsyncSession = Depends(get_session),
):
    """Register a new institution. Requires institution or admin role."""

    if body.institution_type not in VALID_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type: '{body.institution_type}'. Must be: {', '.join(VALID_TYPES)}",
        )

    inst = Institution(
        id=uuid.uuid4(),
        institution_name=body.institution_name,
        institution_type=body.institution_type,
        state=body.state,
        nodal_officer_name=body.nodal_officer_name,
        nodal_officer_email=body.nodal_officer_email,
        nodal_officer_phone=body.nodal_officer_phone,
        funding_source=body.funding_source,
        ibdc_registration_number=body.ibdc_registration_number,
        is_verified=False,
    )
    session.add(inst)
    await session.flush()

    # Link user to institution
    user.institution_id = inst.id

    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="institution.register",
        resource_type="institution",
        resource_id=inst.id,
        details={"institution_name": inst.institution_name},
        ip_address=request.client.host if request.client else None,
    )

    logger.info(f"Institution registered: {inst.institution_name}")
    return _build_response(inst)


@router.post(
    "/verify",
    response_model=InstitutionResponse,
    summary="Verify an institution (admin only)",
)
async def verify_institution(
    body: InstitutionVerifyRequest,
    request: Request,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    """Admin verifies an institution, enabling them to manage datasets."""

    result = await session.execute(
        select(Institution).where(Institution.id == body.institution_id)
    )
    inst = result.scalar_one_or_none()

    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    if inst.is_verified:
        raise HTTPException(status_code=400, detail="Institution is already verified")

    inst.is_verified = True
    inst.verified_at = datetime.utcnow()
    inst.verified_by = user.id

    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="institution.verify",
        resource_type="institution",
        resource_id=inst.id,
        details={"institution_name": inst.institution_name},
        ip_address=request.client.host if request.client else None,
    )

    # Notify the institution
    if inst.nodal_officer_email:
        notification_service.dispatch(
            NotificationEvent.INSTITUTION_VERIFIED,
            inst.nodal_officer_email,
            {
                "institution_name": inst.institution_name,
                "nodal_officer_name": inst.nodal_officer_name or "Nodal Officer",
            },
        )

    logger.info(f"Institution verified: {inst.institution_name}")

    count_result = await session.execute(
        select(func.count()).select_from(Dataset)
        .where(Dataset.managing_institution_id == inst.id)
    )
    return _build_response(inst, count_result.scalar_one())


@router.get(
    "",
    response_model=InstitutionListResponse,
    summary="List all verified institutions",
)
async def list_institutions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    include_unverified: bool = Query(False, description="Include unverified (admin only)"),
    session: AsyncSession = Depends(get_session),
):
    """List institutions. By default only verified institutions are shown."""

    query = select(Institution)
    count_query = select(func.count()).select_from(Institution)

    if not include_unverified:
        query = query.where(Institution.is_verified == True)
        count_query = count_query.where(Institution.is_verified == True)

    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * limit
    query = query.order_by(Institution.created_at.desc()).offset(offset).limit(limit)

    result = await session.execute(query)
    institutions = result.scalars().all()

    data = []
    for inst in institutions:
        count_result = await session.execute(
            select(func.count()).select_from(Dataset)
            .where(Dataset.managing_institution_id == inst.id)
        )
        data.append(_build_response(inst, count_result.scalar_one()))

    return InstitutionListResponse(
        data=data,
        pagination=PaginationMeta(
            page=page, limit=limit, total=total,
            total_pages=math.ceil(total / limit) if total > 0 else 0,
        ),
    )


@router.get(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Get institution profile",
)
async def get_institution(
    institution_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single institution's profile and dataset count."""

    result = await session.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    inst = result.scalar_one_or_none()

    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    count_result = await session.execute(
        select(func.count()).select_from(Dataset)
        .where(Dataset.managing_institution_id == inst.id)
    )
    return _build_response(inst, count_result.scalar_one())


@router.put(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Update institution profile",
)
async def update_institution(
    institution_id: uuid.UUID,
    body: InstitutionUpdateRequest,
    request: Request,
    user: User = Depends(require_role("institution", "admin")),
    session: AsyncSession = Depends(get_session),
):
    """Update institution profile. Only the owning institution or admin can update."""

    result = await session.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    inst = result.scalar_one_or_none()

    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Check ownership (unless admin)
    if user.role != "admin" and user.institution_id != inst.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this institution")

    # Apply updates
    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(inst, field, value)
    inst.updated_at = datetime.utcnow()

    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="institution.update",
        resource_type="institution",
        resource_id=inst.id,
        details=update_data,
        ip_address=request.client.host if request.client else None,
    )

    count_result = await session.execute(
        select(func.count()).select_from(Dataset)
        .where(Dataset.managing_institution_id == inst.id)
    )
    return _build_response(inst, count_result.scalar_one())
