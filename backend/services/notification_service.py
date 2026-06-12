"""
BioNexus India V2 — Notification Service

Async notification system with pluggable channel architecture.
Currently implements EmailChannel; designed so SMS/WhatsApp channels
can be added later without changing core logic.

Notifications are dispatched via Celery tasks — they NEVER block
API responses. If Celery/Redis is unavailable, notifications are
logged to console as fallback.

Channel architecture:
    NotificationChannel (ABC)
        ├── EmailChannel      (implemented)
        ├── SMSChannel        (future V3)
        └── WhatsAppChannel   (future V3)
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Notification Event Types
# =============================================================================

class NotificationEvent:
    """Constants for notification event types."""
    REQUEST_SUBMITTED = "request_submitted"
    REQUEST_APPROVED = "request_approved"
    REQUEST_REJECTED = "request_rejected"
    MORE_INFO_NEEDED = "more_info_needed"
    INFO_RESPONSE_RECEIVED = "info_response_received"
    ACCESS_EXPIRING = "access_expiring"
    INSTITUTION_VERIFIED = "institution_verified"
    USER_REGISTERED = "user_registered"


# Event → email template mapping
EMAIL_TEMPLATES: dict[str, dict[str, str]] = {
    NotificationEvent.REQUEST_SUBMITTED: {
        "subject": "[BioNexus] New Data Access Request — {dataset_name}",
        "body": (
            "Dear {nodal_officer_name},\n\n"
            "A new data access request has been submitted on BioNexus India.\n\n"
            "Researcher: {researcher_name} ({researcher_email})\n"
            "Dataset: {dataset_name}\n"
            "Purpose: {purpose_of_use}\n"
            "Institution: {institution_affiliation}\n\n"
            "Please log in to BioNexus to review this request.\n\n"
            "— BioNexus India Platform"
        ),
    },
    NotificationEvent.REQUEST_APPROVED: {
        "subject": "[BioNexus] Access Request Approved — {dataset_name}",
        "body": (
            "Dear {researcher_name},\n\n"
            "Your data access request for '{dataset_name}' has been APPROVED.\n\n"
            "Access valid until: {expires_at}\n"
            "FeED compliance forms are available in your dashboard.\n\n"
            "Please ensure you comply with the Data User Agreement terms.\n\n"
            "— BioNexus India Platform"
        ),
    },
    NotificationEvent.REQUEST_REJECTED: {
        "subject": "[BioNexus] Access Request Declined — {dataset_name}",
        "body": (
            "Dear {researcher_name},\n\n"
            "Your data access request for '{dataset_name}' has been declined.\n\n"
            "Reason: {rejection_reason}\n\n"
            "You may submit a new request addressing the concerns above.\n\n"
            "— BioNexus India Platform"
        ),
    },
    NotificationEvent.MORE_INFO_NEEDED: {
        "subject": "[BioNexus] Additional Information Required — {dataset_name}",
        "body": (
            "Dear {researcher_name},\n\n"
            "The reviewing institution requires additional information for your "
            "access request for '{dataset_name}'.\n\n"
            "Message from reviewer:\n{info_request_message}\n\n"
            "Please log in to BioNexus to respond.\n\n"
            "— BioNexus India Platform"
        ),
    },
    NotificationEvent.INFO_RESPONSE_RECEIVED: {
        "subject": "[BioNexus] Researcher Response Received — {dataset_name}",
        "body": (
            "Dear {nodal_officer_name},\n\n"
            "The researcher {researcher_name} has responded to your information "
            "request regarding '{dataset_name}'.\n\n"
            "Response:\n{info_response_message}\n\n"
            "Please log in to BioNexus to continue review.\n\n"
            "— BioNexus India Platform"
        ),
    },
    NotificationEvent.ACCESS_EXPIRING: {
        "subject": "[BioNexus] Access Expiring Soon — {dataset_name}",
        "body": (
            "Dear {researcher_name},\n\n"
            "Your access to '{dataset_name}' will expire on {expires_at}.\n\n"
            "If you need continued access, please submit a renewal request.\n\n"
            "— BioNexus India Platform"
        ),
    },
    NotificationEvent.INSTITUTION_VERIFIED: {
        "subject": "[BioNexus] Institution Verified — {institution_name}",
        "body": (
            "Dear {nodal_officer_name},\n\n"
            "Your institution '{institution_name}' has been verified on BioNexus India.\n\n"
            "You can now manage datasets and review access requests.\n\n"
            "— BioNexus India Platform"
        ),
    },
    NotificationEvent.USER_REGISTERED: {
        "subject": "Welcome to BioNexus India",
        "body": (
            "Dear {full_name},\n\n"
            "Welcome to BioNexus India — India's first unified bioinformatics "
            "metadata platform.\n\n"
            "Your account has been created with role: {role}\n\n"
            "Visit the platform to discover Indian biological datasets.\n\n"
            "— BioNexus India Platform"
        ),
    },
}


# =============================================================================
# Channel Abstraction
# =============================================================================


class NotificationChannel(ABC):
    """
    Abstract base class for notification channels.

    To add a new channel (e.g., SMS), subclass and implement send().
    Then register the channel with NotificationService.
    """

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Unique identifier for the channel."""
        ...

    @abstractmethod
    async def send(
        self, to: str, subject: str, body: str, **kwargs
    ) -> bool:
        """
        Send a notification.

        Args:
            to: Recipient identifier (email, phone, etc.)
            subject: Notification subject
            body: Notification body

        Returns:
            True if sent successfully, False otherwise.
        """
        ...


class EmailChannel(NotificationChannel):
    """
    Email notification channel using SMTP.

    If SMTP is not configured (smtp_host is empty), falls back to
    console logging — suitable for development.
    """

    channel_name = "email"

    async def send(
        self, to: str, subject: str, body: str, **kwargs
    ) -> bool:
        """Send an email notification."""
        if not settings.smtp_host:
            # Dev mode — log to console
            logger.info(
                f"[EMAIL-DEV] To: {to}\n"
                f"  Subject: {subject}\n"
                f"  Body:\n{body}\n"
            )
            return True

        try:
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
            logger.info(f"Email sent to {to}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}", exc_info=True)
            return False


# =============================================================================
# Notification Service
# =============================================================================


class NotificationService:
    """
    Dispatches notifications through registered channels.

    In production, notifications are sent via Celery tasks (async).
    If Celery/Redis is unavailable, falls back to synchronous delivery.
    """

    def __init__(self):
        self.channels: list[NotificationChannel] = [EmailChannel()]

    def dispatch(
        self,
        event_type: str,
        recipient_email: str,
        context: dict[str, Any],
    ) -> None:
        """
        Dispatch a notification via Celery task queue.

        Falls back to console logging if Celery is unavailable.
        """
        template = EMAIL_TEMPLATES.get(event_type)
        if not template:
            logger.warning(f"No template for event: {event_type}")
            return

        try:
            subject = template["subject"].format(**context)
            body = template["body"].format(**context)
        except KeyError as e:
            logger.error(
                f"Template rendering failed for {event_type}: missing key {e}"
            )
            return

        # Try dispatching via Celery (with timeout to never block API)
        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

            def _dispatch():
                from workers.notification_worker import send_notification_task
                send_notification_task.delay(
                    recipient_email=recipient_email,
                    subject=subject,
                    body=body,
                    event_type=event_type,
                )

            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(_dispatch)
            try:
                future.result(timeout=2)  # 2 second max wait
                logger.info(
                    f"Notification queued: {event_type} → {recipient_email}"
                )
            except FuturesTimeout:
                logger.warning(
                    f"Celery dispatch timed out (Redis unavailable?), falling back to log"
                )
                future.cancel()
                self._fallback_log(event_type, recipient_email, subject, body)
            finally:
                executor.shutdown(wait=False)

        except Exception as e:
            # Celery/Redis unavailable — log as fallback
            logger.warning(
                f"Celery unavailable, logging notification: {e}"
            )
            self._fallback_log(event_type, recipient_email, subject, body)

    def _fallback_log(self, event_type: str, to: str, subject: str, body: str):
        """Log notification to console when Celery is unavailable."""
        logger.info(
            f"[NOTIFICATION-FALLBACK] {event_type}\n"
            f"  To: {to}\n"
            f"  Subject: {subject}\n"
            f"  Body:\n{body}\n"
        )


# Singleton instance
notification_service = NotificationService()
