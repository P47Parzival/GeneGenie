"""
BioNexus India V2 — Database ORM Models

V1 Models (unchanged):
  - Dataset: Unified metadata record for any Indian biological dataset
  - IngestionLog: Tracks each pipeline run for observability

V2 Models (new):
  - User: Platform users with role-based access
  - Institution: Registered and verified institutions
  - AccessRequest: Dataset access request lifecycle
  - AccessRequestDocument: File uploads for access requests
  - AccessRequestTransition: State transition audit log
  - FeedForm: Generated FeED compliance forms
  - AuditLog: Immutable, append-only platform audit trail
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# =============================================================================
# V1 Models (unchanged)
# =============================================================================


class Dataset(Base):
    """
    Unified metadata record for an Indian biological dataset.

    Every dataset ingested from any source (IndiGenomes, IBDC, GenomeIndia, etc.)
    is stored in this table with a standardized schema. Fields that are unavailable
    from a particular source are stored as NULL — we never fail on missing data.
    """

    __tablename__ = "datasets"

    # --- Primary Key ---
    dataset_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the dataset (UUID4 or UUID5 for dedup)",
    )

    # --- Core Metadata ---
    name = Column(Text, nullable=False, comment="Dataset name / title")
    source = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Source system: indigenomes, ibdc, genomeindia, etc.",
    )
    institution_name = Column(Text, nullable=True, comment="Originating institution")
    state_of_collection = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Indian state where samples were collected",
    )
    population_group = Column(
        String(200),
        nullable=True,
        index=True,
        comment="Population/ethnic group of subjects",
    )
    data_type = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Type: genomic, clinical, imaging, other",
    )
    disease_association = Column(
        Text,
        nullable=True,
        comment="Associated disease(s) or phenotype(s)",
    )
    sample_size = Column(Integer, nullable=True, comment="Number of samples/subjects")
    collection_date = Column(
        Date, nullable=True, comment="Date of data collection"
    )
    access_type = Column(
        String(20),
        nullable=True,
        index=True,
        comment="Access level: open, managed, controlled",
    )

    # --- Provenance ---
    source_url = Column(Text, nullable=True, comment="URL to original dataset")
    ethics_approval_number = Column(
        String(100), nullable=True, comment="Ethics committee approval ID"
    )
    contact_researcher = Column(
        Text, nullable=True, comment="Primary contact for the dataset"
    )
    license_type = Column(
        String(100), nullable=True, comment="Data license: CC-BY, restricted, etc."
    )
    doi = Column(String(200), nullable=True, comment="Digital Object Identifier")
    raw_checksum = Column(
        String(64),
        nullable=True,
        comment="SHA-256 checksum of the raw ingested record (for change detection)",
    )

    # --- V2: Institution linkage ---
    managing_institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id"),
        nullable=True,
        comment="Institution that manages this dataset (V2)",
    )

    # --- Timestamps ---
    date_ingested = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="When this record was ingested into BioNexus",
    )

    # --- Full-Text Search Vector ---
    search_vector = Column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', "
            "coalesce(name, '') || ' ' || "
            "coalesce(institution_name, '') || ' ' || "
            "coalesce(disease_association, '') || ' ' || "
            "coalesce(population_group, '') || ' ' || "
            "coalesce(state_of_collection, '') || ' ' || "
            "coalesce(source, '')"
            ")",
            persisted=True,
        ),
        comment="Auto-generated tsvector for full-text search",
    )

    # --- Relationships ---
    managing_institution = relationship(
        "Institution", back_populates="datasets", lazy="selectin"
    )
    access_requests = relationship(
        "AccessRequest", back_populates="dataset", lazy="selectin"
    )

    # --- Table-Level Indexes ---
    __table_args__ = (
        Index("ix_datasets_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_datasets_disease_association", "disease_association"),
        Index("ix_datasets_source_date_ingested", "source", "date_ingested"),
        {"comment": "Unified metadata store for Indian biological datasets"},
    )

    def __repr__(self) -> str:
        return f"<Dataset(id={self.dataset_id}, name='{self.name}', source='{self.source}')>"


class IngestionLog(Base):
    """
    Tracks each pipeline run for observability.

    Every time an ingestion pipeline runs (whether triggered via API or scheduled),
    a log entry is created with the outcome.
    """

    __tablename__ = "ingestion_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(
        String(100), nullable=False, index=True, comment="Source that was ingested"
    )
    status = Column(
        String(20),
        nullable=False,
        comment="Status: running, success, partial_failure, failure",
    )
    records_fetched = Column(Integer, nullable=True)
    records_ingested = Column(Integer, nullable=True)
    records_failed = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<IngestionLog(source='{self.source}', status='{self.status}', "
            f"ingested={self.records_ingested})>"
        )


# =============================================================================
# V2 Models
# =============================================================================


class User(Base):
    """
    Platform user with role-based access control.

    Roles:
      - researcher: searches datasets, requests access
      - institution: manages datasets, reviews access requests
      - admin: platform oversight, manages institutions
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Login identifier — must be unique",
    )
    hashed_password = Column(
        Text, nullable=False, comment="bcrypt hashed password — never store plaintext"
    )
    full_name = Column(Text, nullable=False, comment="User's full name")
    role = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Role: researcher, institution, admin",
    )
    institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id"),
        nullable=True,
        comment="Linked institution (for institution-role users)",
    )
    is_active = Column(
        Boolean, nullable=False, default=True, server_default="true",
        comment="Whether this account is active",
    )
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow,
        server_default=func.now(), onupdate=datetime.utcnow,
    )

    # --- Relationships ---
    institution = relationship(
        "Institution", back_populates="users",
        foreign_keys=[institution_id], lazy="selectin",
    )
    access_requests = relationship(
        "AccessRequest", back_populates="requesting_user",
        foreign_keys="AccessRequest.requesting_user_id", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(email='{self.email}', role='{self.role}')>"


class Institution(Base):
    """
    Registered institution on the platform.

    Institutions must be verified by an admin before they can manage
    datasets and review access requests.
    """

    __tablename__ = "institutions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_name = Column(
        Text, nullable=False, comment="Official institution name"
    )
    institution_type = Column(
        String(20), nullable=False,
        comment="Type: government, private, academic",
    )
    state = Column(String(100), nullable=True, comment="Indian state")
    nodal_officer_name = Column(
        Text, nullable=True, comment="Primary contact / nodal officer"
    )
    nodal_officer_email = Column(
        String(255), nullable=True, comment="Nodal officer email"
    )
    nodal_officer_phone = Column(
        String(20), nullable=True, comment="Nodal officer phone"
    )
    funding_source = Column(
        String(50), nullable=True,
        comment="Funding: DBT, ICMR, DST, state, private",
    )
    ibdc_registration_number = Column(
        String(100), nullable=True,
        comment="IBDC registration number if applicable",
    )
    is_verified = Column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="Whether this institution has been verified by admin",
    )
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
        comment="Admin who verified this institution",
    )
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow,
        server_default=func.now(), onupdate=datetime.utcnow,
    )

    # --- Relationships ---
    users = relationship(
        "User", back_populates="institution",
        foreign_keys="User.institution_id", lazy="selectin",
    )
    verifier = relationship(
        "User", foreign_keys=[verified_by], lazy="selectin",
    )
    datasets = relationship("Dataset", back_populates="managing_institution", lazy="selectin")

    __table_args__ = (
        Index("ix_institutions_is_verified", "is_verified"),
        Index("ix_institutions_state", "state"),
    )

    def __repr__(self) -> str:
        return f"<Institution(name='{self.institution_name}', verified={self.is_verified})>"


class AccessRequest(Base):
    """
    Dataset access request with full lifecycle state machine.

    States: DRAFT → SUBMITTED → UNDER_REVIEW →
            APPROVED / REJECTED / MORE_INFO_NEEDED
    """

    __tablename__ = "access_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requesting_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
        comment="Researcher who is requesting access",
    )
    dataset_id = Column(
        UUID(as_uuid=True), ForeignKey("datasets.dataset_id"), nullable=False,
        comment="Dataset being requested",
    )
    status = Column(
        String(30), nullable=False, default="draft", server_default="draft",
        index=True,
        comment="Current status: draft, submitted, under_review, approved, rejected, more_info_needed",
    )
    purpose_of_use = Column(
        Text, nullable=True, comment="Stated purpose for accessing the data"
    )
    institution_affiliation = Column(
        Text, nullable=True, comment="Researcher's institution"
    )
    expected_duration_days = Column(
        Integer, nullable=True, comment="Expected duration of data use in days"
    )
    will_data_be_published = Column(
        Boolean, nullable=True, comment="Whether research will be published"
    )
    ethics_approval_number = Column(
        String(100), nullable=True,
        comment="Researcher's ethics approval if applicable",
    )
    requested_access_type = Column(
        String(20), nullable=True, comment="Requested: open, managed, controlled"
    )

    # --- Review fields ---
    reviewer_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
        comment="Institution user who is reviewing",
    )
    rejection_reason = Column(Text, nullable=True)
    info_request_message = Column(
        Text, nullable=True, comment="Message when institution requests more info"
    )
    info_response_message = Column(
        Text, nullable=True, comment="Researcher's response to info request"
    )

    # --- Timestamps ---
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    expires_at = Column(
        DateTime, nullable=True,
        comment="When approved access expires",
    )
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow,
        server_default=func.now(), onupdate=datetime.utcnow,
    )

    # --- Relationships ---
    requesting_user = relationship(
        "User", back_populates="access_requests",
        foreign_keys=[requesting_user_id], lazy="selectin",
    )
    reviewer = relationship(
        "User", foreign_keys=[reviewer_id], lazy="selectin",
    )
    dataset = relationship(
        "Dataset", back_populates="access_requests", lazy="selectin",
    )
    documents = relationship(
        "AccessRequestDocument", back_populates="access_request",
        lazy="selectin", cascade="all, delete-orphan",
    )
    transitions = relationship(
        "AccessRequestTransition", back_populates="access_request",
        lazy="selectin", cascade="all, delete-orphan",
        order_by="AccessRequestTransition.transitioned_at",
    )
    feed_forms = relationship(
        "FeedForm", back_populates="access_request",
        lazy="selectin", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_access_requests_user", "requesting_user_id"),
        Index("ix_access_requests_dataset", "dataset_id"),
        Index("ix_access_requests_status", "status"),
        Index("ix_access_requests_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<AccessRequest(id={self.id}, status='{self.status}')>"


class AccessRequestDocument(Base):
    """File upload attached to an access request (supporting documents)."""

    __tablename__ = "access_request_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    access_request_id = Column(
        UUID(as_uuid=True), ForeignKey("access_requests.id"), nullable=False
    )
    filename = Column(Text, nullable=False, comment="Original filename")
    file_path = Column(Text, nullable=False, comment="Server storage path")
    file_size = Column(Integer, nullable=False, comment="File size in bytes")
    content_type = Column(
        String(100), nullable=False, comment="MIME type"
    )
    uploaded_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    # --- Relationships ---
    access_request = relationship(
        "AccessRequest", back_populates="documents", lazy="selectin"
    )


class AccessRequestTransition(Base):
    """
    Immutable log of every state transition in an access request.
    Every status change is recorded with who, when, and why.
    """

    __tablename__ = "access_request_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    access_request_id = Column(
        UUID(as_uuid=True), ForeignKey("access_requests.id"), nullable=False
    )
    from_status = Column(String(30), nullable=True, comment="Previous status")
    to_status = Column(String(30), nullable=False, comment="New status")
    actor_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
        comment="User who triggered the transition",
    )
    reason = Column(Text, nullable=True, comment="Reason for the transition")
    transitioned_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    # --- Relationships ---
    access_request = relationship(
        "AccessRequest", back_populates="transitions", lazy="selectin"
    )
    actor = relationship("User", lazy="selectin")

    __table_args__ = (
        Index("ix_ar_transitions_request", "access_request_id"),
    )


class FeedForm(Base):
    """
    Generated FeED (Fair Exchange of Experimental Data) compliance form.

    Each access request can have multiple form types generated:
    DUA, access request form, institutional sign-off, DMP, etc.
    Stored as both structured JSON and rendered PDF.
    """

    __tablename__ = "feed_forms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    access_request_id = Column(
        UUID(as_uuid=True), ForeignKey("access_requests.id"), nullable=False
    )
    form_type = Column(
        String(50), nullable=False,
        comment="Form type: dua, access_request, signoff, dmp, publication, ethics",
    )
    form_data_json = Column(
        JSONB, nullable=False,
        comment="Structured form content as JSON",
    )
    pdf_path = Column(
        Text, nullable=True, comment="Path to generated PDF file"
    )
    signed_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
        comment="Institution user who signed/acknowledged this form",
    )
    signed_at = Column(DateTime, nullable=True)
    generated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    # --- Relationships ---
    access_request = relationship(
        "AccessRequest", back_populates="feed_forms", lazy="selectin"
    )
    signer = relationship("User", lazy="selectin")

    __table_args__ = (
        Index("ix_feed_forms_request", "access_request_id"),
        Index("ix_feed_forms_type", "form_type"),
    )


class AuditLog(Base):
    """
    Immutable, append-only audit trail.

    NEVER update or delete records from this table. Every action on
    the platform is logged here for compliance and traceability.
    """

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
        comment="User who performed the action (NULL for system actions)",
    )
    action = Column(
        String(100), nullable=False,
        comment="Action identifier, e.g. 'access_request.submit'",
    )
    resource_type = Column(
        String(50), nullable=False,
        comment="Resource type, e.g. 'access_request', 'institution'",
    )
    resource_id = Column(
        UUID(as_uuid=True), nullable=False,
        comment="ID of the resource acted upon",
    )
    details = Column(
        JSONB, nullable=True,
        comment="Action-specific metadata",
    )
    ip_address = Column(
        String(45), nullable=True,
        comment="IP address of the actor (IPv4 or IPv6)",
    )
    timestamp = Column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    # --- Relationships ---
    actor = relationship("User", lazy="selectin")

    __table_args__ = (
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_actor", "actor_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(action='{self.action}', resource={self.resource_type}/"
            f"{self.resource_id}, actor={self.actor_id})>"
        )
