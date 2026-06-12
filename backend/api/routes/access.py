"""
BioNexus India V2 — Access Request Routes

Full lifecycle state machine:
  DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED / REJECTED / MORE_INFO_NEEDED

POST /access-requests              — create draft
GET  /access-requests              — list (filtered by role)
GET  /access-requests/{id}         — full details
PUT  /access-requests/{id}/submit  — submit draft
PUT  /access-requests/{id}/review  — start review
PUT  /access-requests/{id}/approve — approve
PUT  /access-requests/{id}/reject  — reject with reason
PUT  /access-requests/{id}/info    — request more info
PUT  /access-requests/{id}/respond — respond to info request
POST /access-requests/{id}/documents — upload supporting docs
"""

import logging
import math
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import (
    APIRouter, Depends, File, HTTPException,
    Query, Request, UploadFile, status,
)
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    AccessRequestCreate,
    AccessRequestResponse,
    AccessRequestListResponse,
    AccessRequestTransitionResponse,
    ReviewActionRequest,
    InfoResponseRequest,
    DocumentResponse,
    PaginationMeta,
)
from config import settings
from database import get_session
from database.models import (
    AccessRequest, AccessRequestDocument, AccessRequestTransition,
    Dataset, Institution, User,
)
from services.auth_service import get_current_user, require_role
from services.audit_service import audit_service
from services.notification_service import notification_service, NotificationEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/access-requests", tags=["Access Requests"])

# Valid state transitions
VALID_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["submitted"],
    "submitted": ["under_review"],
    "under_review": ["approved", "rejected", "more_info_needed"],
    "more_info_needed": ["under_review"],  # After researcher responds
}

ALLOWED_UPLOAD_TYPES = {
    "application/pdf",
    "image/png", "image/jpeg",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


def _build_response(ar: AccessRequest) -> AccessRequestResponse:
    """Build access request response with nested data."""
    return AccessRequestResponse(
        id=ar.id,
        requesting_user_id=ar.requesting_user_id,
        dataset_id=ar.dataset_id,
        status=ar.status,
        purpose_of_use=ar.purpose_of_use,
        institution_affiliation=ar.institution_affiliation,
        expected_duration_days=ar.expected_duration_days,
        will_data_be_published=ar.will_data_be_published,
        ethics_approval_number=ar.ethics_approval_number,
        requested_access_type=ar.requested_access_type,
        reviewer_id=ar.reviewer_id,
        rejection_reason=ar.rejection_reason,
        info_request_message=ar.info_request_message,
        info_response_message=ar.info_response_message,
        submitted_at=ar.submitted_at,
        approved_at=ar.approved_at,
        rejected_at=ar.rejected_at,
        expires_at=ar.expires_at,
        created_at=ar.created_at,
        updated_at=ar.updated_at,
        transitions=[
            AccessRequestTransitionResponse.model_validate(t)
            for t in (ar.transitions or [])
        ],
        documents=[
            DocumentResponse.model_validate(d) for d in (ar.documents or [])
        ],
        researcher_name=ar.requesting_user.full_name if ar.requesting_user else None,
        dataset_name=ar.dataset.name if ar.dataset else None,
    )


async def _record_transition(
    session: AsyncSession,
    ar: AccessRequest,
    to_status: str,
    actor: User,
    reason: str | None = None,
):
    """Record a state transition in the transition log."""
    transition = AccessRequestTransition(
        id=uuid.uuid4(),
        access_request_id=ar.id,
        from_status=ar.status,
        to_status=to_status,
        actor_id=actor.id,
        reason=reason,
    )
    session.add(transition)
    ar.status = to_status
    ar.updated_at = datetime.utcnow()


@router.post(
    "",
    response_model=AccessRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create access request (draft)",
)
async def create_request(
    body: AccessRequestCreate,
    request: Request,
    user: User = Depends(require_role("researcher")),
    session: AsyncSession = Depends(get_session),
):
    """Create a new access request in DRAFT status."""

    # Verify dataset exists
    result = await session.execute(
        select(Dataset).where(Dataset.dataset_id == body.dataset_id)
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    ar = AccessRequest(
        id=uuid.uuid4(),
        requesting_user_id=user.id,
        dataset_id=body.dataset_id,
        status="draft",
        purpose_of_use=body.purpose_of_use,
        institution_affiliation=body.institution_affiliation,
        expected_duration_days=body.expected_duration_days,
        will_data_be_published=body.will_data_be_published,
        ethics_approval_number=body.ethics_approval_number,
        requested_access_type=body.requested_access_type,
    )
    session.add(ar)
    await session.flush()

    # Record initial transition
    await _record_transition(session, ar, "draft", user, "Request created")
    ar.status = "draft"  # Keep as draft since _record_transition updates it

    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="access_request.create",
        resource_type="access_request",
        resource_id=ar.id,
        details={"dataset_id": str(body.dataset_id), "status": "draft"},
        ip_address=request.client.host if request.client else None,
    )

    # Re-fetch with relationships
    result = await session.execute(
        select(AccessRequest).where(AccessRequest.id == ar.id)
    )
    ar = result.scalar_one()

    logger.info(f"Access request created: {ar.id} by {user.email}")
    return _build_response(ar)


@router.get(
    "",
    response_model=AccessRequestListResponse,
    summary="List access requests (role-filtered)",
)
async def list_requests(
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    List access requests filtered by user role:
    - Researcher: sees own requests
    - Institution: sees requests for their datasets
    - Admin: sees all requests
    """
    query = select(AccessRequest)
    count_query = select(func.count()).select_from(AccessRequest)

    if user.role == "researcher":
        query = query.where(AccessRequest.requesting_user_id == user.id)
        count_query = count_query.where(AccessRequest.requesting_user_id == user.id)
    elif user.role == "institution" and user.institution_id:
        # Get datasets managed by this institution
        dataset_subq = select(Dataset.dataset_id).where(
            Dataset.managing_institution_id == user.institution_id
        ).scalar_subquery()
        query = query.where(AccessRequest.dataset_id.in_(dataset_subq))
        count_query = count_query.where(AccessRequest.dataset_id.in_(dataset_subq))
    # Admin sees all

    if status_filter:
        query = query.where(AccessRequest.status == status_filter)
        count_query = count_query.where(AccessRequest.status == status_filter)

    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * limit
    query = query.order_by(AccessRequest.created_at.desc()).offset(offset).limit(limit)

    result = await session.execute(query)
    requests = result.scalars().all()

    return AccessRequestListResponse(
        data=[_build_response(ar) for ar in requests],
        pagination=PaginationMeta(
            page=page, limit=limit, total=total,
            total_pages=math.ceil(total / limit) if total > 0 else 0,
        ),
    )


@router.get(
    "/{request_id}",
    response_model=AccessRequestResponse,
    summary="Get access request details",
)
async def get_request(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get full details of an access request."""

    result = await session.execute(
        select(AccessRequest).where(AccessRequest.id == request_id)
    )
    ar = result.scalar_one_or_none()

    if not ar:
        raise HTTPException(status_code=404, detail="Access request not found")

    # Authorization: only involved parties or admin
    if user.role == "researcher" and ar.requesting_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if user.role == "institution":
        ds = ar.dataset
        if not ds or ds.managing_institution_id != user.institution_id:
            raise HTTPException(status_code=403, detail="Not authorized")

    return _build_response(ar)


@router.put(
    "/{request_id}/submit",
    response_model=AccessRequestResponse,
    summary="Submit draft request",
)
async def submit_request(
    request_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("researcher")),
    session: AsyncSession = Depends(get_session),
):
    """Submit a draft access request for review."""

    result = await session.execute(
        select(AccessRequest).where(AccessRequest.id == request_id)
    )
    ar = result.scalar_one_or_none()

    if not ar:
        raise HTTPException(status_code=404, detail="Access request not found")
    if ar.requesting_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your request")
    if ar.status != "draft":
        raise HTTPException(status_code=400, detail=f"Cannot submit from status '{ar.status}'")

    # Validate required fields
    if not ar.purpose_of_use:
        raise HTTPException(status_code=400, detail="Purpose of use is required before submitting")

    await _record_transition(session, ar, "submitted", user, "Submitted for review")
    ar.submitted_at = datetime.utcnow()

    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="access_request.submit",
        resource_type="access_request",
        resource_id=ar.id,
        ip_address=request.client.host if request.client else None,
    )

    # Notify institution
    dataset = ar.dataset
    if dataset and dataset.managing_institution_id:
        inst_result = await session.execute(
            select(Institution).where(Institution.id == dataset.managing_institution_id)
        )
        inst = inst_result.scalar_one_or_none()
        if inst and inst.nodal_officer_email:
            notification_service.dispatch(
                NotificationEvent.REQUEST_SUBMITTED,
                inst.nodal_officer_email,
                {
                    "nodal_officer_name": inst.nodal_officer_name or "Nodal Officer",
                    "researcher_name": user.full_name,
                    "researcher_email": user.email,
                    "dataset_name": dataset.name,
                    "purpose_of_use": ar.purpose_of_use or "Not specified",
                    "institution_affiliation": ar.institution_affiliation or "Not specified",
                },
            )

    return _build_response(ar)


@router.put(
    "/{request_id}/review",
    response_model=AccessRequestResponse,
    summary="Start reviewing request",
)
async def start_review(
    request_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("institution", "admin")),
    session: AsyncSession = Depends(get_session),
):
    """Institution marks request as under review."""

    ar = await _get_request_for_institution(request_id, user, session)

    if ar.status not in ("submitted", "more_info_needed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start review from status '{ar.status}'",
        )

    await _record_transition(session, ar, "under_review", user, "Review started")
    ar.reviewer_id = user.id

    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="access_request.review",
        resource_type="access_request",
        resource_id=ar.id,
        ip_address=request.client.host if request.client else None,
    )

    return _build_response(ar)


@router.put(
    "/{request_id}/approve",
    response_model=AccessRequestResponse,
    summary="Approve access request",
)
async def approve_request(
    request_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("institution", "admin")),
    session: AsyncSession = Depends(get_session),
):
    """Institution approves the access request."""

    ar = await _get_request_for_institution(request_id, user, session)

    if ar.status != "under_review":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve from status '{ar.status}'. Must be 'under_review'.",
        )

    await _record_transition(session, ar, "approved", user, "Access granted")
    ar.approved_at = datetime.utcnow()
    ar.reviewer_id = user.id

    # Set expiry based on requested duration
    if ar.expected_duration_days:
        ar.expires_at = datetime.utcnow() + timedelta(days=ar.expected_duration_days)

    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="access_request.approve",
        resource_type="access_request",
        resource_id=ar.id,
        details={"expires_at": ar.expires_at.isoformat() if ar.expires_at else None},
        ip_address=request.client.host if request.client else None,
    )

    # Notify researcher
    researcher = ar.requesting_user
    dataset = ar.dataset
    if researcher and dataset:
        notification_service.dispatch(
            NotificationEvent.REQUEST_APPROVED,
            researcher.email,
            {
                "researcher_name": researcher.full_name,
                "dataset_name": dataset.name,
                "expires_at": ar.expires_at.strftime("%d %B %Y") if ar.expires_at else "No expiry",
            },
        )

    logger.info(f"Access request {ar.id} APPROVED by {user.email}")
    return _build_response(ar)


@router.put(
    "/{request_id}/reject",
    response_model=AccessRequestResponse,
    summary="Reject access request",
)
async def reject_request(
    request_id: uuid.UUID,
    body: ReviewActionRequest,
    request: Request,
    user: User = Depends(require_role("institution", "admin")),
    session: AsyncSession = Depends(get_session),
):
    """Institution rejects the access request with a reason."""

    ar = await _get_request_for_institution(request_id, user, session)

    if ar.status != "under_review":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject from status '{ar.status}'",
        )

    await _record_transition(session, ar, "rejected", user, body.reason)
    ar.rejected_at = datetime.utcnow()
    ar.rejection_reason = body.reason
    ar.reviewer_id = user.id

    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="access_request.reject",
        resource_type="access_request",
        resource_id=ar.id,
        details={"reason": body.reason},
        ip_address=request.client.host if request.client else None,
    )

    # Notify researcher
    researcher = ar.requesting_user
    dataset = ar.dataset
    if researcher and dataset:
        notification_service.dispatch(
            NotificationEvent.REQUEST_REJECTED,
            researcher.email,
            {
                "researcher_name": researcher.full_name,
                "dataset_name": dataset.name,
                "rejection_reason": body.reason or "No reason provided",
            },
        )

    logger.info(f"Access request {ar.id} REJECTED by {user.email}")
    return _build_response(ar)


@router.put(
    "/{request_id}/info",
    response_model=AccessRequestResponse,
    summary="Request more information",
)
async def request_info(
    request_id: uuid.UUID,
    body: ReviewActionRequest,
    request: Request,
    user: User = Depends(require_role("institution", "admin")),
    session: AsyncSession = Depends(get_session),
):
    """Institution requests more information from the researcher."""

    ar = await _get_request_for_institution(request_id, user, session)

    if ar.status != "under_review":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot request info from status '{ar.status}'",
        )

    await _record_transition(session, ar, "more_info_needed", user, body.reason)
    ar.info_request_message = body.reason
    ar.reviewer_id = user.id

    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="access_request.request_info",
        resource_type="access_request",
        resource_id=ar.id,
        details={"message": body.reason},
        ip_address=request.client.host if request.client else None,
    )

    # Notify researcher
    researcher = ar.requesting_user
    dataset = ar.dataset
    if researcher and dataset:
        notification_service.dispatch(
            NotificationEvent.MORE_INFO_NEEDED,
            researcher.email,
            {
                "researcher_name": researcher.full_name,
                "dataset_name": dataset.name,
                "info_request_message": body.reason or "Additional information needed",
            },
        )

    return _build_response(ar)


@router.put(
    "/{request_id}/respond",
    response_model=AccessRequestResponse,
    summary="Respond to info request",
)
async def respond_to_info(
    request_id: uuid.UUID,
    body: InfoResponseRequest,
    request: Request,
    user: User = Depends(require_role("researcher")),
    session: AsyncSession = Depends(get_session),
):
    """Researcher responds to an institution's information request."""

    result = await session.execute(
        select(AccessRequest).where(AccessRequest.id == request_id)
    )
    ar = result.scalar_one_or_none()

    if not ar:
        raise HTTPException(status_code=404, detail="Access request not found")
    if ar.requesting_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your request")
    if ar.status != "more_info_needed":
        raise HTTPException(
            status_code=400,
            detail=f"No info request pending (status: '{ar.status}')",
        )

    ar.info_response_message = body.message
    # Auto-transition back to under_review
    await _record_transition(session, ar, "under_review", user, f"Info provided: {body.message}")

    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="access_request.respond_info",
        resource_type="access_request",
        resource_id=ar.id,
        details={"response": body.message},
        ip_address=request.client.host if request.client else None,
    )

    # Notify reviewer
    dataset = ar.dataset
    if ar.reviewer_id and dataset:
        reviewer_result = await session.execute(
            select(User).where(User.id == ar.reviewer_id)
        )
        reviewer = reviewer_result.scalar_one_or_none()
        if reviewer:
            # Find institution for nodal officer name
            inst = None
            if dataset.managing_institution_id:
                inst_result = await session.execute(
                    select(Institution).where(Institution.id == dataset.managing_institution_id)
                )
                inst = inst_result.scalar_one_or_none()

            notification_service.dispatch(
                NotificationEvent.INFO_RESPONSE_RECEIVED,
                reviewer.email,
                {
                    "nodal_officer_name": inst.nodal_officer_name if inst else reviewer.full_name,
                    "researcher_name": user.full_name,
                    "dataset_name": dataset.name,
                    "info_response_message": body.message,
                },
            )

    return _build_response(ar)


@router.post(
    "/{request_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload supporting document",
)
async def upload_document(
    request_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_role("researcher")),
    session: AsyncSession = Depends(get_session),
):
    """Upload a supporting document for an access request."""

    result = await session.execute(
        select(AccessRequest).where(AccessRequest.id == request_id)
    )
    ar = result.scalar_one_or_none()

    if not ar:
        raise HTTPException(status_code=404, detail="Access request not found")
    if ar.requesting_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your request")
    if ar.status not in ("draft", "more_info_needed"):
        raise HTTPException(
            status_code=400,
            detail="Can only upload documents when request is in draft or more_info_needed status",
        )

    # Validate file type
    if file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file.content_type}' not allowed. Allowed: {', '.join(ALLOWED_UPLOAD_TYPES)}",
        )

    # Read and validate size
    content = await file.read()
    max_size = settings.max_upload_size_mb * 1024 * 1024

    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds {settings.max_upload_size_mb}MB limit",
        )

    # Save file
    upload_dir = Path(settings.upload_dir) / "documents" / str(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    # Create document record
    doc = AccessRequestDocument(
        id=uuid.uuid4(),
        access_request_id=ar.id,
        filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        content_type=file.content_type,
    )
    session.add(doc)

    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="access_request.upload_document",
        resource_type="access_request",
        resource_id=ar.id,
        details={"filename": file.filename, "size": len(content)},
        ip_address=request.client.host if request.client else None,
    )

    logger.info(f"Document uploaded for request {ar.id}: {file.filename}")
    return DocumentResponse.model_validate(doc)


async def _get_request_for_institution(
    request_id: uuid.UUID,
    user: User,
    session: AsyncSession,
) -> AccessRequest:
    """Get an access request and verify institution authorization."""

    result = await session.execute(
        select(AccessRequest).where(AccessRequest.id == request_id)
    )
    ar = result.scalar_one_or_none()

    if not ar:
        raise HTTPException(status_code=404, detail="Access request not found")

    # Admin can access any request
    if user.role == "admin":
        return ar

    # Institution user must be linked to the dataset's institution
    dataset = ar.dataset
    if not dataset or dataset.managing_institution_id != user.institution_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized — this dataset is not managed by your institution",
        )

    return ar
