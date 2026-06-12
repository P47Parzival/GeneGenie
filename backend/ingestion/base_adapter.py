"""
BioNexus India V1 — Base Adapter

Abstract base class for all data source adapters. Every new data source
integration only needs to subclass BaseAdapter and implement:
  - source_name: str property
  - base_url: str property
  - fetch_datasets(): the source-specific fetch logic

The base class provides:
  - HTTP client with timeout and retry (exponential backoff)
  - Raw response storage for debugging
  - Structured logging with source context
  - Graceful error handling

To add a new data source, create a new file in ingestion/ and subclass:

    class MyNewAdapter(BaseAdapter):
        source_name = "my_source"
        base_url = "https://example.com"

        async def fetch_datasets(self) -> list[dict]:
            # Your scraping/API logic here
            ...
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from config import settings

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """
    Abstract base class for all BioNexus data source adapters.

    Subclasses must define:
        source_name: Unique identifier for the source (e.g., "indigenomes")
        base_url: Base URL of the data source
        fetch_datasets(): Async method that returns raw metadata dicts
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this data source."""
        ...

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL of the data source."""
        ...

    def __init__(self):
        """Initialize the adapter with an HTTP client."""
        self._client: httpx.AsyncClient | None = None
        self._logger = logging.getLogger(f"{__name__}.{self.source_name}")

    async def __aenter__(self):
        """Async context manager entry — creates HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.ingestion_timeout),
            follow_redirects=True,
            headers={
                "User-Agent": "BioNexus-India/1.0 (metadata-ingestion; https://bionexus.in)",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit — closes HTTP client."""
        if self._client:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(settings.ingestion_max_retries),
        wait=wait_exponential(
            multiplier=settings.ingestion_backoff_base,
            min=1,
            max=30,
        ),
        retry=retry_if_exception_type(
            (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _fetch_url(self, url: str, **kwargs) -> httpx.Response:
        """
        Fetch a URL with automatic retry and exponential backoff.

        Retries on:
          - HTTP 5xx errors
          - Connection errors
          - Read timeouts

        Does NOT retry on:
          - 4xx client errors (those indicate a real problem)
          - Other unexpected exceptions
        """
        self._logger.info(f"Fetching: {url}")
        response = await self._client.get(url, **kwargs)

        # Raise on 5xx so tenacity retries; let 4xx pass through
        if response.status_code >= 500:
            response.raise_for_status()

        return response

    def _store_raw_response(self, data: Any, suffix: str = "") -> Path:
        """
        Store raw fetched data to disk for debugging and audit trail.

        Returns the path where the raw data was stored.
        """
        raw_dir = Path(settings.raw_data_dir) / self.source_name
        raw_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}{('_' + suffix) if suffix else ''}.json"
        filepath = raw_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        self._logger.info(f"Raw response stored: {filepath}")
        return filepath

    @abstractmethod
    async def fetch_datasets(self) -> list[dict]:
        """
        Fetch dataset metadata from the source.

        Returns a list of raw dictionaries — one per dataset found.
        The keys/structure will be source-specific; the Transformer
        handles mapping these to the unified schema.

        This method should:
          - Handle pagination if applicable
          - Catch and log individual record errors without failing
          - Store raw responses via self._store_raw_response()
        """
        ...

    async def run(self) -> list[dict]:
        """
        Execute the full adapter pipeline.

        Opens HTTP client, fetches datasets, stores raw data,
        and returns the raw metadata records.
        """
        self._logger.info(
            f"Starting ingestion from {self.source_name} ({self.base_url})"
        )

        try:
            async with self:
                raw_datasets = await self.fetch_datasets()

            self._logger.info(
                f"Ingestion complete: {len(raw_datasets)} records "
                f"fetched from {self.source_name}"
            )
            return raw_datasets

        except Exception as e:
            self._logger.error(
                f"Ingestion failed for {self.source_name}: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise
