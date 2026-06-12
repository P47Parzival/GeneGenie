"""Initial schema — datasets and ingestion_logs tables

Revision ID: 001_initial_schema
Revises: None
Create Date: 2025-01-15 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- datasets table ---
    op.create_table(
        "datasets",
        sa.Column("dataset_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("institution_name", sa.Text(), nullable=True),
        sa.Column("state_of_collection", sa.String(100), nullable=True),
        sa.Column("population_group", sa.String(200), nullable=True),
        sa.Column("data_type", sa.String(50), nullable=True),
        sa.Column("disease_association", sa.Text(), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("collection_date", sa.Date(), nullable=True),
        sa.Column("access_type", sa.String(20), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("ethics_approval_number", sa.String(100), nullable=True),
        sa.Column("contact_researcher", sa.Text(), nullable=True),
        sa.Column("license_type", sa.String(100), nullable=True),
        sa.Column("doi", sa.String(200), nullable=True),
        sa.Column("raw_checksum", sa.String(64), nullable=True),
        sa.Column(
            "date_ingested",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "search_vector",
            TSVECTOR(),
            sa.Computed(
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
            nullable=True,
        ),
        comment="Unified metadata store for Indian biological datasets",
    )

    # B-tree indexes for filter queries
    op.create_index("ix_datasets_source", "datasets", ["source"])
    op.create_index(
        "ix_datasets_state_of_collection", "datasets", ["state_of_collection"]
    )
    op.create_index("ix_datasets_population_group", "datasets", ["population_group"])
    op.create_index("ix_datasets_data_type", "datasets", ["data_type"])
    op.create_index("ix_datasets_access_type", "datasets", ["access_type"])
    op.create_index(
        "ix_datasets_disease_association", "datasets", ["disease_association"]
    )
    op.create_index(
        "ix_datasets_source_date_ingested", "datasets", ["source", "date_ingested"]
    )

    # GIN index for full-text search
    op.create_index(
        "ix_datasets_search_vector",
        "datasets",
        ["search_vector"],
        postgresql_using="gin",
    )

    # --- ingestion_logs table ---
    op.create_table(
        "ingestion_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("records_fetched", sa.Integer(), nullable=True),
        sa.Column("records_ingested", sa.Integer(), nullable=True),
        sa.Column("records_failed", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    op.create_index("ix_ingestion_logs_source", "ingestion_logs", ["source"])


def downgrade() -> None:
    op.drop_table("ingestion_logs")
    op.drop_table("datasets")
