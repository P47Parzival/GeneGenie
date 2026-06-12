"""
BioNexus India V2 — FeED Form Routes

POST /feed-forms/generate          — generate forms for an access request
GET  /feed-forms/{request_id}      — retrieve generated forms
POST /feed-forms/{request_id}/sign — institution signs/acknowledges
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    FeedFormGenerateRequest,
    FeedFormResponse,
    FeedFormListResponse,
    ErrorResponse,
)
from database import get_session
from database.models import (
    AccessRequest, Dataset, FeedForm, Institution, User,
)
from services.auth_service import get_current_user, require_role
from services.audit_service import audit_service
from services.feed_form_service import feed_form_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feed-forms", tags=["FeED Forms"])


@router.post(
    "/generate",
    response_model=FeedFormListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate FeED compliance forms",
)
async def generate_forms(
    body: FeedFormGenerateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Generate FeED-compliant forms for an access request.

    Generates 6 form types: DUA, Access Request, Signoff, DMP,
    Publication, Ethics. Each form is stored as both JSON and PDF.

    Can be called by the requesting researcher, the institution,
    or an admin.
    """
    # Fetch access request
    result = await session.execute(
        select(AccessRequest).where(AccessRequest.id == body.access_request_id)
    )
    ar = result.scalar_one_or_none()

    if not ar:
        raise HTTPException(status_code=404, detail="Access request not found")

    # Authorization: researcher, owning institution, or admin
    if user.role == "researcher" and ar.requesting_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your request")

    # Fetch related data
    dataset = ar.dataset
    if not dataset:
        raise HTTPException(status_code=404, detail="Associated dataset not found")

    researcher = ar.requesting_user

    # Fetch institution if linked
    institution = None
    if dataset.managing_institution_id:
        inst_result = await session.execute(
            select(Institution).where(Institution.id == dataset.managing_institution_id)
        )
        institution = inst_result.scalar_one_or_none()

    # Generate all forms
    form_data_list = feed_form_service.generate_all_forms(
        access_request=ar,
        dataset=dataset,
        researcher=researcher,
        institution=institution,
    )

    # Store forms in database
    db_forms = []
    for fd in form_data_list:
        form = FeedForm(
            id=uuid.uuid4(),
            access_request_id=ar.id,
            form_type=fd["form_type"],
            form_data_json=fd["form_data_json"],
            pdf_path=fd.get("pdf_path"),
        )
        session.add(form)
        db_forms.append(form)

    await session.flush()

    # Audit
    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="feed_form.generate",
        resource_type="access_request",
        resource_id=ar.id,
        details={"forms_generated": len(db_forms)},
        ip_address=request.client.host if request.client else None,
    )

    logger.info(
        f"Generated {len(db_forms)} FeED forms for request {ar.id}"
    )

    return FeedFormListResponse(
        access_request_id=ar.id,
        forms=[FeedFormResponse.model_validate(f) for f in db_forms],
    )


@router.get(
    "/{request_id}",
    response_model=FeedFormListResponse,
    summary="Get generated FeED forms",
)
async def get_forms(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Retrieve all generated FeED forms for an access request."""

    # Verify access request exists and user is authorized
    ar_result = await session.execute(
        select(AccessRequest).where(AccessRequest.id == request_id)
    )
    ar = ar_result.scalar_one_or_none()

    if not ar:
        raise HTTPException(status_code=404, detail="Access request not found")

    # Authorization
    if user.role == "researcher" and ar.requesting_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Fetch forms
    result = await session.execute(
        select(FeedForm)
        .where(FeedForm.access_request_id == request_id)
        .order_by(FeedForm.generated_at)
    )
    forms = result.scalars().all()

    if not forms:
        raise HTTPException(
            status_code=404,
            detail="No forms generated yet. Call POST /feed-forms/generate first.",
        )

    return FeedFormListResponse(
        access_request_id=request_id,
        forms=[FeedFormResponse.model_validate(f) for f in forms],
    )


@router.post(
    "/{request_id}/sign",
    response_model=FeedFormListResponse,
    summary="Sign/acknowledge FeED forms",
)
async def sign_forms(
    request_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("institution", "admin")),
    session: AsyncSession = Depends(get_session),
):
    """
    Institution digitally acknowledges all FeED forms for a request.

    Sets the signed_by and signed_at fields on all unsigned forms.
    """
    # Verify access request
    ar_result = await session.execute(
        select(AccessRequest).where(AccessRequest.id == request_id)
    )
    ar = ar_result.scalar_one_or_none()

    if not ar:
        raise HTTPException(status_code=404, detail="Access request not found")

    # Fetch unsigned forms
    result = await session.execute(
        select(FeedForm)
        .where(
            FeedForm.access_request_id == request_id,
            FeedForm.signed_by.is_(None),
        )
    )
    forms = result.scalars().all()

    if not forms:
        raise HTTPException(
            status_code=400,
            detail="No unsigned forms found (all already signed or none generated)",
        )

    now = datetime.utcnow()
    for form in forms:
        form.signed_by = user.id
        form.signed_at = now

    # Audit
    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="feed_form.sign",
        resource_type="access_request",
        resource_id=ar.id,
        details={"forms_signed": len(forms)},
        ip_address=request.client.host if request.client else None,
    )

    # Re-fetch all forms
    all_result = await session.execute(
        select(FeedForm)
        .where(FeedForm.access_request_id == request_id)
        .order_by(FeedForm.generated_at)
    )
    all_forms = all_result.scalars().all()

    logger.info(f"Signed {len(forms)} FeED forms for request {request_id}")

    return FeedFormListResponse(
        access_request_id=request_id,
        forms=[FeedFormResponse.model_validate(f) for f in all_forms],
    )
