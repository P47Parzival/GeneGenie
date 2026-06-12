"""
BioNexus India V2 — API Schemas (Pydantic Models)

Defines all request/response models for the API.
V1 schemas are preserved; V2 schemas are added below.

Every response includes consistent metadata: pagination, timestamps,
and source attribution.
"""

import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, EmailStr


# =============================================================================
# Pagination (V1 — unchanged)
# =============================================================================


class PaginationMeta(BaseModel):
    """Pagination metadata included in every list response."""

    page: int = Field(description="Current page number (1-indexed)")
    limit: int = Field(description="Items per page")
    total: int = Field(description="Total matching records")
    total_pages: int = Field(description="Total pages available")


# =============================================================================
# Dataset (V1 — extended with public/authenticated split)
# =============================================================================


class DatasetPublicResponse(BaseModel):
    """Limited dataset metadata for unauthenticated access."""

    dataset_id: uuid.UUID
    name: str
    source: str
    institution_name: str | None = None
    state_of_collection: str | None = None
    population_group: str | None = None
    data_type: str | None = None
    disease_association: str | None = None
    sample_size: int | None = None
    access_type: str | None = None
    date_ingested: datetime | None = None

    model_config = {"from_attributes": True}


class DatasetResponse(BaseModel):
    """Full metadata for a single dataset (authenticated access)."""

    dataset_id: uuid.UUID
    name: str
    source: str
    institution_name: str | None = None
    state_of_collection: str | None = None
    population_group: str | None = None
    data_type: str | None = None
    disease_association: str | None = None
    sample_size: int | None = None
    collection_date: date | None = None
    access_type: str | None = None
    source_url: str | None = None
    ethics_approval_number: str | None = None
    contact_researcher: str | None = None
    license_type: str | None = None
    doi: str | None = None
    raw_checksum: str | None = None
    date_ingested: datetime | None = None
    managing_institution_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    """Paginated list of datasets with metadata."""

    data: list[DatasetResponse | DatasetPublicResponse]
    pagination: PaginationMeta
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Search (V1 — unchanged)
# =============================================================================


class SearchResponse(BaseModel):
    """Search results with query echo and pagination."""

    query: str = Field(description="The search query that was executed")
    data: list[DatasetResponse | DatasetPublicResponse]
    pagination: PaginationMeta
    filters_applied: dict[str, str] = Field(
        default_factory=dict,
        description="Active filters applied to the search",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Ingestion (V1 — unchanged)
# =============================================================================


class IngestRequest(BaseModel):
    source: str = Field(description="Source to ingest from")


class IngestResponse(BaseModel):
    source: str
    status: str
    records_fetched: int | None = None
    records_ingested: int | None = None
    records_failed: int | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Sources (V1 — unchanged)
# =============================================================================


class SourceInfo(BaseModel):
    name: str
    last_ingestion_at: datetime | None = None
    last_ingestion_status: str | None = None
    total_datasets: int = 0


class SourcesResponse(BaseModel):
    sources: list[SourceInfo]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Stats (V1 — unchanged)
# =============================================================================


class StatsBreakdown(BaseModel):
    category: str
    count: int


class StatsResponse(BaseModel):
    total_datasets: int
    by_source: list[StatsBreakdown]
    by_data_type: list[StatsBreakdown]
    by_state: list[StatsBreakdown]
    by_population: list[StatsBreakdown]
    by_access_type: list[StatsBreakdown]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Error (V1 — unchanged)
# =============================================================================


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# V2: Authentication
# =============================================================================


class RegisterRequest(BaseModel):
    """User registration request."""
    email: str = Field(..., min_length=5, max_length=255, description="Email address")
    password: str = Field(..., min_length=8, max_length=100, description="Password (min 8 chars)")
    full_name: str = Field(..., min_length=2, max_length=200, description="Full name")
    role: str = Field(
        default="researcher",
        description="Role: researcher, institution, admin",
    )


class LoginRequest(BaseModel):
    """User login request."""
    email: str = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """JWT token pair response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds")
    user: "UserResponse"


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., description="Valid refresh token")


class UserResponse(BaseModel):
    """User profile response."""
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    institution_id: uuid.UUID | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """User profile update."""
    full_name: str | None = None
    email: str | None = None


# =============================================================================
# V2: Institutions
# =============================================================================


class InstitutionRegisterRequest(BaseModel):
    """Institution registration request."""
    institution_name: str = Field(..., min_length=3, max_length=500)
    institution_type: str = Field(
        ..., description="Type: government, private, academic"
    )
    state: str | None = Field(None, max_length=100)
    nodal_officer_name: str | None = None
    nodal_officer_email: str | None = None
    nodal_officer_phone: str | None = Field(None, max_length=20)
    funding_source: str | None = Field(
        None, description="DBT, ICMR, DST, state, private"
    )
    ibdc_registration_number: str | None = None


class InstitutionUpdateRequest(BaseModel):
    """Institution profile update."""
    institution_name: str | None = None
    institution_type: str | None = None
    state: str | None = None
    nodal_officer_name: str | None = None
    nodal_officer_email: str | None = None
    nodal_officer_phone: str | None = None
    funding_source: str | None = None
    ibdc_registration_number: str | None = None


class InstitutionVerifyRequest(BaseModel):
    """Admin request to verify an institution."""
    institution_id: uuid.UUID


class InstitutionResponse(BaseModel):
    """Institution profile response."""
    id: uuid.UUID
    institution_name: str
    institution_type: str
    state: str | None = None
    nodal_officer_name: str | None = None
    nodal_officer_email: str | None = None
    nodal_officer_phone: str | None = None
    funding_source: str | None = None
    ibdc_registration_number: str | None = None
    is_verified: bool
    verified_at: datetime | None = None
    created_at: datetime
    dataset_count: int = 0

    model_config = {"from_attributes": True}


class InstitutionListResponse(BaseModel):
    """Paginated list of institutions."""
    data: list[InstitutionResponse]
    pagination: PaginationMeta
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# V2: Access Requests
# =============================================================================


class AccessRequestCreate(BaseModel):
    """Create a new access request (draft)."""
    dataset_id: uuid.UUID
    purpose_of_use: str | None = None
    institution_affiliation: str | None = None
    expected_duration_days: int | None = Field(None, ge=1, le=3650)
    will_data_be_published: bool | None = None
    ethics_approval_number: str | None = None
    requested_access_type: str | None = Field(
        None, description="open, managed, controlled"
    )


class AccessRequestUpdate(BaseModel):
    """Update access request fields (while in draft)."""
    purpose_of_use: str | None = None
    institution_affiliation: str | None = None
    expected_duration_days: int | None = None
    will_data_be_published: bool | None = None
    ethics_approval_number: str | None = None
    requested_access_type: str | None = None


class ReviewActionRequest(BaseModel):
    """Request body for review actions (reject, info request)."""
    reason: str | None = Field(None, description="Reason for rejection or info request message")


class InfoResponseRequest(BaseModel):
    """Researcher's response to an information request."""
    message: str = Field(..., min_length=1, description="Response message")


class AccessRequestTransitionResponse(BaseModel):
    """State transition log entry."""
    id: uuid.UUID
    from_status: str | None = None
    to_status: str
    actor_id: uuid.UUID
    reason: str | None = None
    transitioned_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    """Uploaded document metadata."""
    id: uuid.UUID
    filename: str
    file_size: int
    content_type: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class AccessRequestResponse(BaseModel):
    """Full access request response."""
    id: uuid.UUID
    requesting_user_id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    purpose_of_use: str | None = None
    institution_affiliation: str | None = None
    expected_duration_days: int | None = None
    will_data_be_published: bool | None = None
    ethics_approval_number: str | None = None
    requested_access_type: str | None = None
    reviewer_id: uuid.UUID | None = None
    rejection_reason: str | None = None
    info_request_message: str | None = None
    info_response_message: str | None = None
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # Nested
    transitions: list[AccessRequestTransitionResponse] = []
    documents: list[DocumentResponse] = []
    researcher_name: str | None = None
    dataset_name: str | None = None

    model_config = {"from_attributes": True}


class AccessRequestListResponse(BaseModel):
    """Paginated list of access requests."""
    data: list[AccessRequestResponse]
    pagination: PaginationMeta
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# V2: FeED Forms
# =============================================================================


class FeedFormGenerateRequest(BaseModel):
    """Request to generate FeED forms."""
    access_request_id: uuid.UUID


class FeedFormResponse(BaseModel):
    """Generated FeED form response."""
    id: uuid.UUID
    access_request_id: uuid.UUID
    form_type: str
    form_data_json: dict[str, Any]
    pdf_path: str | None = None
    signed_by: uuid.UUID | None = None
    signed_at: datetime | None = None
    generated_at: datetime

    model_config = {"from_attributes": True}


class FeedFormListResponse(BaseModel):
    """List of generated FeED forms."""
    access_request_id: uuid.UUID
    forms: list[FeedFormResponse]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FeedFormSignRequest(BaseModel):
    """Request to sign/acknowledge a FeED form."""
    pass  # Signing user is derived from auth token


# =============================================================================
# V2: Audit
# =============================================================================


class AuditLogResponse(BaseModel):
    """Audit log entry."""
    id: uuid.UUID
    actor_id: uuid.UUID | None = None
    action: str
    resource_type: str
    resource_id: uuid.UUID
    details: dict[str, Any] | None = None
    ip_address: str | None = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """List of audit log entries."""
    resource_type: str
    resource_id: uuid.UUID
    entries: list[AuditLogResponse]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
