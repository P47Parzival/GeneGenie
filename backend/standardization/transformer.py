"""
BioNexus India V1 — Metadata Transformer

Takes raw output from any adapter and maps it to the unified metadata schema.
Every dataset that passes through comes out in identical structure regardless
of source. Missing fields are set to None — never fails on incomplete data.

Every transformation is logged:
  - What fields were mapped
  - What fields were missing
  - What defaults were applied

The transformer is source-agnostic by design — it uses field name matching
and source-specific mappings to handle different input formats.
"""

import hashlib
import json
import logging
import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StandardizedDataset(BaseModel):
    """
    Pydantic model representing a fully standardized dataset record.

    This is the output of the transformation pipeline — every dataset
    in BioNexus has exactly this structure, regardless of source.
    """

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
    date_ingested: datetime = Field(default_factory=datetime.utcnow)


# Field alias mappings: maps various raw field names to our unified schema.
# Keys are unified schema field names; values are lists of possible raw field
# names (case-insensitive) that should map to that field.
FIELD_ALIASES: dict[str, list[str]] = {
    "name": [
        "name", "title", "dataset_name", "study_name", "project_name",
        "dataset_title", "study_title",
    ],
    "source": [
        "source", "data_source", "repository", "origin",
    ],
    "institution_name": [
        "institution_name", "institution", "institute", "organization",
        "organisation", "center", "centre", "lab", "laboratory",
        "submitter", "submitted_by",
    ],
    "state_of_collection": [
        "state_of_collection", "state", "region", "location",
        "collection_location", "geography", "province",
    ],
    "population_group": [
        "population_group", "population", "ethnic_group", "ethnicity",
        "community", "caste", "tribe", "linguistic_group",
    ],
    "data_type": [
        "data_type", "type", "datatype", "data_category", "category",
        "experiment_type", "assay_type",
    ],
    "disease_association": [
        "disease_association", "disease", "phenotype", "condition",
        "disorder", "trait", "diagnosis", "disease_name",
        "description",
    ],
    "sample_size": [
        "sample_size", "samples", "num_samples", "n", "count",
        "subjects", "num_subjects", "participants", "size",
    ],
    "collection_date": [
        "collection_date", "date", "year", "study_date",
        "submission_date", "release_date", "published_date",
    ],
    "access_type": [
        "access_type", "access", "access_level", "availability",
        "data_access", "sharing",
    ],
    "source_url": [
        "source_url", "url", "link", "href", "uri",
        "dataset_url", "download_url", "web_url",
    ],
    "ethics_approval_number": [
        "ethics_approval_number", "ethics", "irb", "ethics_id",
        "ethics_committee", "approval_number",
    ],
    "contact_researcher": [
        "contact_researcher", "contact", "researcher", "pi",
        "principal_investigator", "corresponding_author", "author",
        "submitter_name",
    ],
    "license_type": [
        "license_type", "license", "licence", "data_license",
        "terms", "usage_terms",
    ],
    "doi": [
        "doi", "digital_object_identifier", "publication_doi",
    ],
}

# Valid values for constrained fields
VALID_DATA_TYPES = {"genomic", "clinical", "imaging", "other"}
VALID_ACCESS_TYPES = {"open", "managed", "controlled"}


class MetadataTransformer:
    """
    Transforms raw adapter output into standardized dataset records.

    The transformer is designed to be resilient:
      - Missing fields → None (never fails)
      - Unknown data types → "other"
      - Malformed dates → None with warning
      - Every transformation is logged
    """

    def transform_batch(
        self, raw_records: list[dict], source: str
    ) -> list[StandardizedDataset]:
        """
        Transform a batch of raw records into standardized datasets.

        Args:
            raw_records: List of raw dicts from an adapter
            source: Source identifier (e.g., "indigenomes")

        Returns:
            List of StandardizedDataset models
        """
        results = []
        for i, raw in enumerate(raw_records):
            try:
                standardized = self.transform_single(raw, source=source)
                results.append(standardized)
            except Exception as e:
                logger.error(
                    f"Transform failed for record #{i} from {source}: "
                    f"{type(e).__name__}: {e}",
                    exc_info=True,
                )
                # Never fail on a single record — skip and continue
                continue

        logger.info(
            f"Transform batch complete: {len(results)}/{len(raw_records)} "
            f"records standardized for source '{source}'"
        )
        return results

    def transform_single(
        self, raw: dict, source: str
    ) -> StandardizedDataset:
        """
        Transform a single raw record into a standardized dataset.

        Logs every field: mapped, missing, or defaulted.
        """
        mapped_fields = []
        missing_fields = []
        defaulted_fields = []

        # --- Build the unified record ---
        # Name (required — use fallback if missing)
        name = self._resolve_field(raw, "name")
        if name:
            mapped_fields.append("name")
        else:
            name = f"Unnamed dataset from {source}"
            defaulted_fields.append("name")

        # Source (always set from adapter)
        resolved_source = self._resolve_field(raw, "source") or source
        mapped_fields.append("source")

        # Map all optional fields
        institution_name = self._resolve_field(raw, "institution_name")
        self._log_field("institution_name", institution_name, mapped_fields, missing_fields)

        state_of_collection = self._resolve_field(raw, "state_of_collection")
        self._log_field("state_of_collection", state_of_collection, mapped_fields, missing_fields)

        population_group = self._resolve_field(raw, "population_group")
        self._log_field("population_group", population_group, mapped_fields, missing_fields)

        # Data type — normalize to valid values
        data_type_raw = self._resolve_field(raw, "data_type")
        data_type = self._normalize_data_type(data_type_raw)
        if data_type_raw:
            mapped_fields.append("data_type")
            if data_type != data_type_raw:
                defaulted_fields.append(f"data_type ('{data_type_raw}' → '{data_type}')")
        else:
            missing_fields.append("data_type")

        disease_association = self._resolve_field(raw, "disease_association")
        self._log_field("disease_association", disease_association, mapped_fields, missing_fields)

        # Sample size — parse as integer
        sample_size = self._parse_int(self._resolve_field(raw, "sample_size"))
        self._log_field("sample_size", sample_size, mapped_fields, missing_fields)

        # Collection date — parse flexibly
        collection_date = self._parse_date(self._resolve_field(raw, "collection_date"))
        self._log_field("collection_date", collection_date, mapped_fields, missing_fields)

        # Access type — normalize
        access_type_raw = self._resolve_field(raw, "access_type")
        access_type = self._normalize_access_type(access_type_raw)
        if access_type_raw:
            mapped_fields.append("access_type")
        else:
            missing_fields.append("access_type")

        source_url = self._resolve_field(raw, "source_url")
        self._log_field("source_url", source_url, mapped_fields, missing_fields)

        ethics_approval_number = self._resolve_field(raw, "ethics_approval_number")
        self._log_field("ethics_approval_number", ethics_approval_number, mapped_fields, missing_fields)

        contact_researcher = self._resolve_field(raw, "contact_researcher")
        self._log_field("contact_researcher", contact_researcher, mapped_fields, missing_fields)

        license_type = self._resolve_field(raw, "license_type")
        self._log_field("license_type", license_type, mapped_fields, missing_fields)

        doi = self._resolve_field(raw, "doi")
        self._log_field("doi", doi, mapped_fields, missing_fields)

        # Compute raw checksum for change detection
        raw_checksum = self._compute_checksum(raw)

        # Generate deterministic dataset_id (UUID5 from source + URL/name)
        id_seed = f"{resolved_source}:{source_url or name}"
        dataset_id = uuid.uuid5(uuid.NAMESPACE_URL, id_seed)

        # Log transformation summary
        logger.info(
            f"Transformed [{resolved_source}] '{name[:60]}': "
            f"{len(mapped_fields)} mapped, "
            f"{len(missing_fields)} missing, "
            f"{len(defaulted_fields)} defaulted"
        )
        logger.debug(
            f"  Mapped: {mapped_fields}\n"
            f"  Missing: {missing_fields}\n"
            f"  Defaulted: {defaulted_fields}"
        )

        return StandardizedDataset(
            dataset_id=dataset_id,
            name=name,
            source=resolved_source,
            institution_name=institution_name,
            state_of_collection=state_of_collection,
            population_group=population_group,
            data_type=data_type,
            disease_association=disease_association,
            sample_size=sample_size,
            collection_date=collection_date,
            access_type=access_type,
            source_url=source_url,
            ethics_approval_number=ethics_approval_number,
            contact_researcher=contact_researcher,
            license_type=license_type,
            doi=doi,
            raw_checksum=raw_checksum,
        )

    def _resolve_field(self, raw: dict, field_name: str) -> Any | None:
        """
        Resolve a unified field name from a raw record.

        Tries the exact field name first, then all known aliases.
        Matching is case-insensitive.
        """
        # Direct match (case-insensitive)
        for key, value in raw.items():
            if key.lower() == field_name.lower():
                return self._clean_value(value)

        # Try aliases
        aliases = FIELD_ALIASES.get(field_name, [])
        for alias in aliases:
            for key, value in raw.items():
                if key.lower() == alias.lower():
                    return self._clean_value(value)

        return None

    @staticmethod
    def _clean_value(value: Any) -> Any | None:
        """Clean a raw value — strip strings, convert empty to None."""
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value if value else None
        return value

    @staticmethod
    def _normalize_data_type(raw_type: str | None) -> str | None:
        """Normalize data type to one of: genomic, clinical, imaging, other."""
        if raw_type is None:
            return None

        raw_lower = raw_type.lower().strip()

        # Direct match
        if raw_lower in VALID_DATA_TYPES:
            return raw_lower

        # Fuzzy matching
        if any(kw in raw_lower for kw in ["genom", "sequenc", "wgs", "wes", "variant", "snp", "exome"]):
            return "genomic"
        if any(kw in raw_lower for kw in ["clinic", "ehr", "medical", "health", "patient"]):
            return "clinical"
        if any(kw in raw_lower for kw in ["imag", "mri", "ct", "xray", "x-ray", "scan", "radio"]):
            return "imaging"

        return "other"

    @staticmethod
    def _normalize_access_type(raw_type: str | None) -> str | None:
        """Normalize access type to one of: open, managed, controlled."""
        if raw_type is None:
            return None

        raw_lower = raw_type.lower().strip()

        if raw_lower in VALID_ACCESS_TYPES:
            return raw_lower

        if any(kw in raw_lower for kw in ["open", "public", "free"]):
            return "open"
        if any(kw in raw_lower for kw in ["managed", "registered", "request"]):
            return "managed"
        if any(kw in raw_lower for kw in ["controlled", "restricted", "private", "closed"]):
            return "controlled"

        return raw_lower  # Keep original if we can't classify

    @staticmethod
    def _parse_int(value: Any) -> int | None:
        """Parse a value as integer, returning None on failure."""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            # Remove commas and spaces (e.g., "1,029" → 1029)
            cleaned = value.replace(",", "").replace(" ", "").strip()
            try:
                return int(cleaned)
            except ValueError:
                # Try to extract first number from string
                import re
                match = re.search(r"\d+", cleaned)
                if match:
                    return int(match.group())
                return None
        return None

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        """Parse a value as date, handling various formats."""
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            from dateutil import parser as date_parser

            try:
                return date_parser.parse(value).date()
            except (ValueError, TypeError):
                # Try year-only
                import re
                year_match = re.search(r"\b(19|20)\d{2}\b", value)
                if year_match:
                    return date(int(year_match.group()), 1, 1)
                return None
        return None

    @staticmethod
    def _compute_checksum(raw: dict) -> str:
        """Compute SHA-256 checksum of the raw record for change detection."""
        # Remove internal fields (prefixed with _)
        clean = {k: v for k, v in raw.items() if not k.startswith("_")}
        raw_str = json.dumps(clean, sort_keys=True, default=str)
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    @staticmethod
    def _log_field(
        field_name: str,
        value: Any,
        mapped: list,
        missing: list,
    ):
        """Helper to track whether a field was mapped or missing."""
        if value is not None:
            mapped.append(field_name)
        else:
            missing.append(field_name)
