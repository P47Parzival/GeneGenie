"""
BioNexus India V2 — Audit Service

Immutable, append-only audit logging for the platform.
Every mutation action is recorded with: who, what, to which resource,
when, from which IP, and with what result.

Usage:
    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="access_request.submit",
        resource_type="access_request",
        resource_id=request_id,
        details={"status": "submitted"},
        ip_address=request.client.host,
    )
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """
    Immutable audit trail service.

    Append-only — never updates or deletes audit records.
    """

    async def log(
        self,
        session: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        Record an audit log entry.

        Args:
            session: Database session
            action: Action identifier (e.g., "access_request.submit")
            resource_type: Type of resource (e.g., "access_request")
            resource_id: ID of the resource
            actor_id: User who performed the action (None for system)
            details: Additional context as JSON
            ip_address: IP address of the actor
        """
        entry = AuditLog(
            id=uuid.uuid4(),
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
        )
        session.add(entry)

        logger.info(
            f"AUDIT | {action} | {resource_type}/{resource_id} | "
            f"actor={actor_id} | ip={ip_address}"
        )

        return entry

    async def get_history(
        self,
        session: AsyncSession,
        resource_type: str,
        resource_id: uuid.UUID,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        Retrieve the full audit history for a resource.

        Returns entries ordered by timestamp descending (newest first).
        """
        result = await session.execute(
            select(AuditLog)
            .where(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id,
            )
            .order_by(desc(AuditLog.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_actions(
        self,
        session: AsyncSession,
        actor_id: uuid.UUID,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Retrieve all actions performed by a specific user."""
        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.actor_id == actor_id)
            .order_by(desc(AuditLog.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())


# Singleton instance
audit_service = AuditService()
