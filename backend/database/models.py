"""
BioNexus India V1 — Database ORM Models

Defines the core data models:
  - Dataset: Unified metadata record for any Indian biological dataset
  - IngestionLog: Tracks each pipeline run for observability

All indexes are optimized for the query patterns specified in the V1 spec:
  - Search by disease, population, state, data_type, source, access_type
  - Full-text search across name, institution, disease, population
  - Combination filters
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Column,
    Computed,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


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

    # --- Timestamps ---
    date_ingested = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="When this record was ingested into BioNexus",
    )

    # --- Full-Text Search Vector ---
    # Generated column: PostgreSQL automatically maintains this from the source columns
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

    # --- Table-Level Indexes ---
    __table_args__ = (
        # GIN index for full-text search — critical for /search endpoint
        Index("ix_datasets_search_vector", "search_vector", postgresql_using="gin"),
        # B-tree index on disease_association for filtered queries
        Index("ix_datasets_disease_association", "disease_association"),
        # Composite index for ingestion tracking queries
        Index("ix_datasets_source_date_ingested", "source", "date_ingested"),
        {"comment": "Unified metadata store for Indian biological datasets"},
    )

    def __repr__(self) -> str:
        return f"<Dataset(id={self.dataset_id}, name='{self.name}', source='{self.source}')>"


class IngestionLog(Base):
    """
    Tracks each pipeline run for observability.

    Every time an ingestion pipeline runs (whether triggered via API or scheduled),
    a log entry is created with the outcome: how many records were processed,
    how many succeeded, how many failed, and any error messages.
    """

    __tablename__ = "ingestion_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source = Column(
        String(100), nullable=False, index=True, comment="Source that was ingested"
    )
    status = Column(
        String(20),
        nullable=False,
        comment="Status: running, success, partial_failure, failure",
    )
    records_fetched = Column(
        Integer, nullable=True, comment="Total records fetched from source"
    )
    records_ingested = Column(
        Integer, nullable=True, comment="Records successfully ingested"
    )
    records_failed = Column(
        Integer, nullable=True, comment="Records that failed transformation/insert"
    )
    error_message = Column(
        Text, nullable=True, comment="Error details if status is failure"
    )
    started_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="When this ingestion run started",
    )
    completed_at = Column(
        DateTime, nullable=True, comment="When this ingestion run completed"
    )

    def __repr__(self) -> str:
        return (
            f"<IngestionLog(source='{self.source}', status='{self.status}', "
            f"ingested={self.records_ingested})>"
        )
