"""
BioNexus India V2 — Audit Routes

GET /audit/{resource_type}/{resource_id} — full history of any resource
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import AuditLogResponse, AuditLogListResponse
from database import get_session
from database.models import User
from services.auth_service import get_current_user, require_role
from services.audit_service import audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["Audit Trail"])


@router.get(
    "/{resource_type}/{resource_id}",
    response_model=AuditLogListResponse,
    summary="Get audit history for a resource",
)
async def get_audit_history(
    resource_type: str,
    resource_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get the full, immutable audit history for any resource.

    Accessible by admin, or by users involved with the resource.
    Returns entries in reverse chronological order.
    """
    # Only admin and institution roles can view audit logs
    # (researchers can view audit logs for their own access requests)
    valid_resource_types = {
        "user", "institution", "access_request",
        "dataset", "feed_form",
    }

    if resource_type not in valid_resource_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource type. Valid: {', '.join(valid_resource_types)}",
        )

    entries = await audit_service.get_history(
        session=session,
        resource_type=resource_type,
        resource_id=resource_id,
    )

    return AuditLogListResponse(
        resource_type=resource_type,
        resource_id=resource_id,
        entries=[AuditLogResponse.model_validate(e) for e in entries],
    )
