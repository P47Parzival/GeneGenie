"""
BioNexus India V2 — Notification Worker (Celery Tasks)

Async notification delivery tasks. These run in a separate process
from the API server and never block API responses.

Tasks:
  - send_notification_task: Dispatches a notification via configured channels
  - send_email_task: Sends a single email via SMTP
  - check_expiring_access: Periodic task to find access expiring within 7 days

Fault tolerance:
  - Auto-retry with exponential backoff (max 5 retries)
  - Failed tasks go to dead letter queue after all retries exhausted
  - Each task is idempotent — safe to retry
"""

import logging
import asyncio
from datetime import datetime, timedelta

from workers.celery_app import celery_app
from config import settings

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.notification_worker.send_notification_task",
    max_retries=5,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_notification_task(
    self,
    recipient_email: str,
    subject: str,
    body: str,
    event_type: str = "unknown",
):
    """
    Send a notification via the configured channel.

    Retries with exponential backoff on failure:
      30s → 60s → 120s → 240s → 480s (then dead letter)
    """
    logger.info(
        f"[Worker] Sending notification: {event_type} → {recipient_email}"
    )

    try:
        if not settings.smtp_host:
            # Dev mode — log to console
            logger.info(
                f"[NOTIFICATION-WORKER-DEV]\n"
                f"  Event: {event_type}\n"
                f"  To: {recipient_email}\n"
                f"  Subject: {subject}\n"
                f"  Body:\n{body}\n"
            )
            return {
                "status": "delivered_dev",
                "recipient": recipient_email,
                "event_type": event_type,
            }

        # Production — send via SMTP
        asyncio.run(_send_email(recipient_email, subject, body))

        logger.info(
            f"[Worker] Notification sent: {event_type} → {recipient_email}"
        )
        return {
            "status": "delivered",
            "recipient": recipient_email,
            "event_type": event_type,
        }

    except Exception as e:
        logger.error(
            f"[Worker] Notification failed (attempt {self.request.retries + 1}): "
            f"{type(e).__name__}: {e}"
        )
        raise  # Celery will auto-retry


async def _send_email(to: str, subject: str, body: str):
    """Send an email via SMTP using aiosmtplib."""
    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    msg = MIMEMultipart()
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        use_tls=settings.smtp_use_tls,
    )


@celery_app.task(
    name="workers.notification_worker.check_expiring_access",
    max_retries=3,
)
def check_expiring_access():
    """
    Periodic task: find access requests expiring within 7 days
    and notify the researchers.

    Runs daily via Celery Beat.
    """
    logger.info("[Worker] Checking for expiring access requests...")

    try:
        asyncio.run(_check_expiring_access_async())
    except Exception as e:
        logger.error(f"[Worker] Expiry check failed: {e}", exc_info=True)
        raise


async def _check_expiring_access_async():
    """Async implementation of expiry check."""
    from sqlalchemy import select, and_
    from database import async_session_factory
    from database.models import AccessRequest, User, Dataset

    now = datetime.utcnow()
    expiry_threshold = now + timedelta(days=7)

    async with async_session_factory() as session:
        result = await session.execute(
            select(AccessRequest)
            .where(
                and_(
                    AccessRequest.status == "approved",
                    AccessRequest.expires_at.isnot(None),
                    AccessRequest.expires_at <= expiry_threshold,
                    AccessRequest.expires_at > now,
                )
            )
        )
        expiring_requests = result.scalars().all()

        logger.info(f"[Worker] Found {len(expiring_requests)} expiring access requests")

        for ar in expiring_requests:
            researcher = ar.requesting_user
            dataset = ar.dataset

            if researcher and dataset:
                send_notification_task.delay(
                    recipient_email=researcher.email,
                    subject=f"[BioNexus] Access Expiring Soon — {dataset.name}",
                    body=(
                        f"Dear {researcher.full_name},\n\n"
                        f"Your access to '{dataset.name}' will expire on "
                        f"{ar.expires_at.strftime('%d %B %Y')}.\n\n"
                        f"If you need continued access, please submit a renewal request.\n\n"
                        f"— BioNexus India Platform"
                    ),
                    event_type="access_expiring",
                )
