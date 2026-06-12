"""
BioNexus India V1 — IBDC Adapter

Fetches dataset metadata from the Indian Biological Data Centre
(https://ibdc.rcb.res.in).

IBDC is India's national repository for life science data, hosted at the
Regional Centre for Biotechnology (RCB), Faridabad. It serves as the
designated data repository under DBT's Biotech-PRIDE policy.

Source: Regional Centre for Biotechnology (RCB), Faridabad, Haryana
"""

import logging
from bs4 import BeautifulSoup

from ingestion.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class IBDCAdapter(BaseAdapter):
    """Adapter for the Indian Biological Data Centre (IBDC/RCB)."""

    source_name = "ibdc"
    base_url = "https://ibdc.rcb.res.in"

    # Known sub-pages and API-like endpoints to try
    CATALOG_PATHS = [
        "/",
        "/datasets",
        "/data",
        "/submissions",
        "/browse",
        "/search",
        "/catalog",
    ]

    async def fetch_datasets(self) -> list[dict]:
        """
        Fetch dataset metadata from IBDC.

        IBDC is a data repository that may have a catalog/listing page.
        We attempt to find and scrape dataset listings from known paths.
        """
        datasets = []
        all_raw_data = {}

        for path in self.CATALOG_PATHS:
            url = f"{self.base_url}{path}"
            try:
                response = await self._fetch_url(url)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "lxml")
                    page_data = self._extract_page_data(soup, url)
                    all_raw_data[path] = page_data

                    # Try to parse dataset entries from this page
                    page_datasets = self._parse_datasets_from_page(soup, url)
                    datasets.extend(page_datasets)

                    logger.info(
                        f"IBDC path {path}: found {len(page_datasets)} datasets"
                    )

                elif response.status_code == 404:
                    logger.debug(f"IBDC path {path}: not found (404)")
                else:
                    logger.warning(
                        f"IBDC path {path}: status {response.status_code}"
                    )

            except Exception as e:
                logger.warning(f"Failed to fetch IBDC path {path}: {e}")
                continue

        # Store all raw scraped data
        self._store_raw_response(all_raw_data, suffix="all_pages")

        # If scraping yielded nothing, use known metadata
        if not datasets:
            datasets = self._get_known_metadata()
            logger.info(
                "Using known metadata for IBDC "
                "(live scraping yielded no structured dataset listings)"
            )

        self._store_raw_response(datasets, suffix="final_output")
        return datasets

    def _extract_page_data(self, soup: BeautifulSoup, url: str) -> dict:
        """Extract structured data from a page."""
        return {
            "url": url,
            "title": (
                soup.find("title").get_text(strip=True)
                if soup.find("title")
                else None
            ),
            "headings": [
                h.get_text(strip=True)
                for h in soup.find_all(["h1", "h2", "h3"])
            ],
            "tables": self._extract_tables(soup),
            "cards": self._extract_cards(soup),
            "lists": self._extract_lists(soup),
            "links": [
                {"text": a.get_text(strip=True), "href": a.get("href", "")}
                for a in soup.find_all("a", href=True)
                if a.get_text(strip=True)
            ][:50],
        }

    def _extract_tables(self, soup: BeautifulSoup) -> list[dict]:
        """Extract HTML tables."""
        tables = []
        for table in soup.find_all("table"):
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                if cells:
                    if headers and len(cells) == len(headers):
                        rows.append(dict(zip(headers, cells)))
                    else:
                        rows.append(cells)
            if rows:
                tables.append({"headers": headers, "rows": rows})
        return tables

    def _extract_cards(self, soup: BeautifulSoup) -> list[dict]:
        """Extract card-like elements (common in modern data catalogs)."""
        cards = []
        # Look for common card CSS patterns
        for card in soup.find_all(
            class_=lambda c: c and any(
                kw in str(c).lower()
                for kw in ["card", "dataset", "item", "entry", "result"]
            )
        ):
            card_data = {
                "title": None,
                "text": card.get_text(strip=True)[:300],
                "links": [],
            }
            # Find title within card
            for heading in card.find_all(["h2", "h3", "h4", "h5", "a"]):
                text = heading.get_text(strip=True)
                if text and len(text) > 5:
                    card_data["title"] = text
                    break
            # Find links
            for a in card.find_all("a", href=True):
                card_data["links"].append(
                    {"text": a.get_text(strip=True), "href": a["href"]}
                )
            if card_data["title"]:
                cards.append(card_data)
        return cards

    def _extract_lists(self, soup: BeautifulSoup) -> list[str]:
        """Extract list items that might represent datasets."""
        items = []
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            # Look for items that seem like dataset references
            keywords = [
                "genome", "sequenc", "data", "sample", "study",
                "project", "bioproject", "accession"
            ]
            if any(kw in text.lower() for kw in keywords) and len(text) > 20:
                items.append(text[:300])
        return items

    def _parse_datasets_from_page(
        self, soup: BeautifulSoup, url: str
    ) -> list[dict]:
        """
        Attempt to parse dataset entries from a page.

        Looks for common patterns: tables with dataset info, card layouts,
        or structured listings.
        """
        datasets = []

        # Strategy 1: Parse tables with dataset-like columns
        for table in soup.find_all("table"):
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
            dataset_keywords = [
                "name", "title", "accession", "project", "study",
                "organism", "type", "submitter", "date",
            ]
            if any(kw in " ".join(headers) for kw in dataset_keywords):
                for tr in table.find_all("tr"):
                    cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if cells and len(cells) >= 2:
                        dataset = {
                            "name": cells[0] if cells else "Unknown",
                            "source": self.source_name,
                            "institution_name": "Indian Biological Data Centre (IBDC), RCB Faridabad",
                            "source_url": url,
                            "_raw_row": dict(zip(headers, cells)) if headers else cells,
                        }
                        datasets.append(dataset)

        # Strategy 2: Parse card/item elements
        cards = self._extract_cards(soup)
        for card in cards:
            if card.get("title"):
                datasets.append({
                    "name": card["title"],
                    "source": self.source_name,
                    "institution_name": "Indian Biological Data Centre (IBDC), RCB Faridabad",
                    "source_url": (
                        card["links"][0]["href"]
                        if card.get("links")
                        else url
                    ),
                    "_raw_text": card.get("text", ""),
                })

        return datasets

    def _get_known_metadata(self) -> list[dict]:
        """
        Return known metadata about IBDC datasets.

        Fallback when live scraping doesn't yield structured results.
        """
        return [
            {
                "name": "IBDC — Indian Biological Data Centre Repository",
                "source": self.source_name,
                "institution_name": "Regional Centre for Biotechnology (RCB), Faridabad",
                "state_of_collection": "Multi-state",
                "population_group": "Pan-Indian",
                "data_type": "genomic",
                "disease_association": "Multi-disease repository",
                "access_type": "managed",
                "source_url": "https://ibdc.rcb.res.in",
                "contact_researcher": "IBDC Data Access Committee, RCB",
                "license_type": "DBT Biotech-PRIDE policy",
            },
        ]
