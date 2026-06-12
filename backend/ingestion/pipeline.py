"""
BioNexus India V1 — Ingestion Pipeline Orchestrator

Central pipeline that coordinates the full ingestion workflow:
  1. Resolve source name → adapter class
  2. Run adapter to fetch raw metadata
  3. Pass raw data through the Standardization Transformer
  4. Upsert standardized records into PostgreSQL
  5. Log results to ingestion_logs table

Usage:
    pipeline = IngestionPipeline()
    result = await pipeline.run("indigenomes")
"""

import logging
import uuid
from datetime import datetime
from typing import Type

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from config import settings
from database import async_session_factory
from database.models import Dataset, IngestionLog
from ingestion.base_adapter import BaseAdapter
from ingestion.indigenomes_adapter import IndiGenomesAdapter
from ingestion.ibdc_adapter import IBDCAdapter
from ingestion.genomeindia_adapter import GenomeIndiaAdapter
from standardization.transformer import MetadataTransformer

logger = logging.getLogger(__name__)

# Registry of all available adapters
# To add a new source: import the adapter and add it here
ADAPTER_REGISTRY: dict[str, Type[BaseAdapter]] = {
    "indigenomes": IndiGenomesAdapter,
    "ibdc": IBDCAdapter,
    "genomeindia": GenomeIndiaAdapter,
}


class IngestionPipeline:
    """
    Orchestrates the full data ingestion workflow.

    This class is the single entry point for all ingestion operations.
    It coordinates between adapters, the transformer, and the database.
    """

    def __init__(self):
        self.transformer = MetadataTransformer()

    @staticmethod
    def get_available_sources() -> list[str]:
        """Return list of all registered source names."""
        return list(ADAPTER_REGISTRY.keys())

    @staticmethod
    def get_adapter(source: str) -> BaseAdapter:
        """
        Resolve a source name to an adapter instance.

        Raises ValueError if the source is not registered.
        """
        adapter_class = ADAPTER_REGISTRY.get(source.lower())
        if adapter_class is None:
            available = ", ".join(ADAPTER_REGISTRY.keys())
            raise ValueError(
                f"Unknown source: '{source}'. "
                f"Available sources: {available}"
            )
        return adapter_class()

    async def run(self, source: str) -> dict:
        """
        Run the full ingestion pipeline for a given source.

        Steps:
          1. Create ingestion log entry (status: running)
          2. Fetch raw data via adapter
          3. Transform to unified schema
          4. Upsert into database
          5. Update log entry with results

        Returns a summary dict with counts and status.
        """
        source = source.lower()
        log_id = uuid.uuid4()
        started_at = datetime.utcnow()

        logger.info(f"Pipeline starting for source: {source}")

        # Create initial log entry
        async with async_session_factory() as session:
            log_entry = IngestionLog(
                id=log_id,
                source=source,
                status="running",
                started_at=started_at,
            )
            session.add(log_entry)
            await session.commit()

        try:
            # Step 1: Fetch raw data
            adapter = self.get_adapter(source)
            raw_records = await adapter.run()
            records_fetched = len(raw_records)

            logger.info(
                f"Pipeline [{source}]: fetched {records_fetched} raw records"
            )

            # Step 2: Transform to unified schema
            standardized_records = self.transformer.transform_batch(
                raw_records, source=source
            )

            logger.info(
                f"Pipeline [{source}]: transformed {len(standardized_records)} records"
            )

            # Step 3: Upsert into database
            records_ingested = 0
            records_failed = 0

            async with async_session_factory() as session:
                for record in standardized_records:
                    try:
                        # Upsert: insert or update on conflict
                        stmt = pg_insert(Dataset).values(
                            dataset_id=record.dataset_id,
                            name=record.name,
                            source=record.source,
                            institution_name=record.institution_name,
                            state_of_collection=record.state_of_collection,
                            population_group=record.population_group,
                            data_type=record.data_type,
                            disease_association=record.disease_association,
                            sample_size=record.sample_size,
                            collection_date=record.collection_date,
                            access_type=record.access_type,
                            source_url=record.source_url,
                            ethics_approval_number=record.ethics_approval_number,
                            contact_researcher=record.contact_researcher,
                            license_type=record.license_type,
                            doi=record.doi,
                            raw_checksum=record.raw_checksum,
                            date_ingested=record.date_ingested,
                        )

                        # On conflict (same dataset_id), update all fields
                        stmt = stmt.on_conflict_do_update(
                            index_elements=["dataset_id"],
                            set_={
                                "name": record.name,
                                "source": record.source,
                                "institution_name": record.institution_name,
                                "state_of_collection": record.state_of_collection,
                                "population_group": record.population_group,
                                "data_type": record.data_type,
                                "disease_association": record.disease_association,
                                "sample_size": record.sample_size,
                                "collection_date": record.collection_date,
                                "access_type": record.access_type,
                                "source_url": record.source_url,
                                "ethics_approval_number": record.ethics_approval_number,
                                "contact_researcher": record.contact_researcher,
                                "license_type": record.license_type,
                                "doi": record.doi,
                                "raw_checksum": record.raw_checksum,
                                "date_ingested": record.date_ingested,
                            },
                        )

                        await session.execute(stmt)
                        records_ingested += 1

                    except Exception as e:
                        records_failed += 1
                        logger.error(
                            f"Pipeline [{source}]: failed to insert record "
                            f"'{record.name}': {e}"
                        )

                await session.commit()

            # Step 4: Update log entry with success
            completed_at = datetime.utcnow()
            status = "success" if records_failed == 0 else "partial_failure"

            async with async_session_factory() as session:
                log_entry = await session.get(IngestionLog, log_id)
                if log_entry:
                    log_entry.status = status
                    log_entry.records_fetched = records_fetched
                    log_entry.records_ingested = records_ingested
                    log_entry.records_failed = records_failed
                    log_entry.completed_at = completed_at
                    await session.commit()

            result = {
                "source": source,
                "status": status,
                "records_fetched": records_fetched,
                "records_ingested": records_ingested,
                "records_failed": records_failed,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "duration_seconds": (completed_at - started_at).total_seconds(),
            }

            logger.info(f"Pipeline [{source}]: completed — {result}")
            return result

        except Exception as e:
            # Update log entry with failure
            completed_at = datetime.utcnow()

            async with async_session_factory() as session:
                log_entry = await session.get(IngestionLog, log_id)
                if log_entry:
                    log_entry.status = "failure"
                    log_entry.error_message = f"{type(e).__name__}: {str(e)}"
                    log_entry.completed_at = completed_at
                    await session.commit()

            logger.error(
                f"Pipeline [{source}]: FAILED — {type(e).__name__}: {e}",
                exc_info=True,
            )

            return {
                "source": source,
                "status": "failure",
                "error": f"{type(e).__name__}: {str(e)}",
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "duration_seconds": (completed_at - started_at).total_seconds(),
            }
