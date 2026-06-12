"""V2 — Auth, institutions, access requests, FeED forms, audit trail

Revision ID: 002_v2_auth_access
Revises: 001_initial_schema
Create Date: 2025-06-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "002_v2_auth_access"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # institutions table (must come before users due to FK)
    # =========================================================================
    op.create_table(
        "institutions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("institution_name", sa.Text(), nullable=False),
        sa.Column("institution_type", sa.String(20), nullable=False),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("nodal_officer_name", sa.Text(), nullable=True),
        sa.Column("nodal_officer_email", sa.String(255), nullable=True),
        sa.Column("nodal_officer_phone", sa.String(20), nullable=True),
        sa.Column("funding_source", sa.String(50), nullable=True),
        sa.Column("ibdc_registration_number", sa.String(100), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("verified_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_institutions_is_verified", "institutions", ["is_verified"])
    op.create_index("ix_institutions_state", "institutions", ["state"])

    # =========================================================================
    # users table
    # =========================================================================
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("institution_id", UUID(as_uuid=True),
                  sa.ForeignKey("institutions.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    # Add verified_by FK to institutions now that users table exists
    op.create_foreign_key(
        "fk_institutions_verified_by", "institutions", "users",
        ["verified_by"], ["id"],
    )

    # =========================================================================
    # Add managing_institution_id to datasets (V2 extension)
    # =========================================================================
    op.add_column(
        "datasets",
        sa.Column("managing_institution_id", UUID(as_uuid=True),
                  sa.ForeignKey("institutions.id"), nullable=True),
    )

    # =========================================================================
    # access_requests table
    # =========================================================================
    op.create_table(
        "access_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("requesting_user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("dataset_id", UUID(as_uuid=True),
                  sa.ForeignKey("datasets.dataset_id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("purpose_of_use", sa.Text(), nullable=True),
        sa.Column("institution_affiliation", sa.Text(), nullable=True),
        sa.Column("expected_duration_days", sa.Integer(), nullable=True),
        sa.Column("will_data_be_published", sa.Boolean(), nullable=True),
        sa.Column("ethics_approval_number", sa.String(100), nullable=True),
        sa.Column("requested_access_type", sa.String(20), nullable=True),
        sa.Column("reviewer_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("info_request_message", sa.Text(), nullable=True),
        sa.Column("info_response_message", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_access_requests_user", "access_requests", ["requesting_user_id"])
    op.create_index("ix_access_requests_dataset", "access_requests", ["dataset_id"])
    op.create_index("ix_access_requests_status", "access_requests", ["status"])
    op.create_index("ix_access_requests_expires", "access_requests", ["expires_at"])

    # =========================================================================
    # access_request_documents table
    # =========================================================================
    op.create_table(
        "access_request_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("access_request_id", UUID(as_uuid=True),
                  sa.ForeignKey("access_requests.id"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # =========================================================================
    # access_request_transitions table
    # =========================================================================
    op.create_table(
        "access_request_transitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("access_request_id", UUID(as_uuid=True),
                  sa.ForeignKey("access_requests.id"), nullable=False),
        sa.Column("from_status", sa.String(30), nullable=True),
        sa.Column("to_status", sa.String(30), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("transitioned_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index(
        "ix_ar_transitions_request", "access_request_transitions",
        ["access_request_id"],
    )

    # =========================================================================
    # feed_forms table
    # =========================================================================
    op.create_table(
        "feed_forms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("access_request_id", UUID(as_uuid=True),
                  sa.ForeignKey("access_requests.id"), nullable=False),
        sa.Column("form_type", sa.String(50), nullable=False),
        sa.Column("form_data_json", JSONB(), nullable=False),
        sa.Column("pdf_path", sa.Text(), nullable=True),
        sa.Column("signed_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_feed_forms_request", "feed_forms", ["access_request_id"])
    op.create_index("ix_feed_forms_type", "feed_forms", ["form_type"])

    # =========================================================================
    # audit_logs table (immutable — append only)
    # =========================================================================
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=False),
        sa.Column("details", JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_resource", "audit_logs",
                    ["resource_type", "resource_id"])
    op.create_index("ix_audit_logs_actor", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("feed_forms")
    op.drop_table("access_request_transitions")
    op.drop_table("access_request_documents")
    op.drop_table("access_requests")
    op.drop_column("datasets", "managing_institution_id")
    op.drop_constraint("fk_institutions_verified_by", "institutions", type_="foreignkey")
    op.drop_table("users")
    op.drop_table("institutions")
