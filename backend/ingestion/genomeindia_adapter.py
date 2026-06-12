"""
BioNexus India V1 — GenomeIndia Adapter

Fetches dataset metadata from the GenomeIndia portal
(https://genomeindia.org).

GenomeIndia is a national project to sequence 10,000 Indian genomes,
creating a comprehensive reference database for the Indian population.
Led by the Indian Institute of Science (IISc) and funded by DBT.

Source: Indian Institute of Science (IISc), Bengaluru + consortium partners
"""

import logging
from bs4 import BeautifulSoup

from ingestion.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class GenomeIndiaAdapter(BaseAdapter):
    """Adapter for the GenomeIndia portal (IISc/DBT)."""

    source_name = "genomeindia"
    base_url = "https://genomeindia.org"

    # Pages to crawl for dataset information
    CRAWL_PATHS = [
        "/",
        "/data",
        "/datasets",
        "/about",
        "/research",
        "/publications",
        "/resources",
        "/downloads",
    ]

    async def fetch_datasets(self) -> list[dict]:
        """
        Fetch dataset metadata from GenomeIndia.

        GenomeIndia documents the 10,000 genome project and associated
        population-specific datasets. We scrape available pages for
        information about datasets, populations, and data access.
        """
        datasets = []
        all_raw_data = {}

        for path in self.CRAWL_PATHS:
            url = f"{self.base_url}{path}"
            try:
                response = await self._fetch_url(url)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "lxml")
                    page_data = self._extract_page_data(soup, url)
                    all_raw_data[path] = page_data

                    # Parse datasets from this page
                    page_datasets = self._parse_page(soup, url)
                    datasets.extend(page_datasets)

                    logger.info(
                        f"GenomeIndia path {path}: "
                        f"found {len(page_datasets)} dataset references"
                    )

                elif response.status_code == 404:
                    logger.debug(f"GenomeIndia path {path}: not found")
                else:
                    logger.warning(
                        f"GenomeIndia path {path}: status {response.status_code}"
                    )

            except Exception as e:
                logger.warning(f"Failed to fetch GenomeIndia path {path}: {e}")
                continue

        self._store_raw_response(all_raw_data, suffix="all_pages")

        # If scraping yielded nothing, use known metadata
        if not datasets:
            datasets = self._get_known_metadata()
            logger.info(
                "Using known metadata for GenomeIndia "
                "(live scraping yielded no structured data)"
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
            "paragraphs": [
                p.get_text(strip=True)[:500]
                for p in soup.find_all("p")
                if len(p.get_text(strip=True)) > 30
            ][:20],
            "tables": self._extract_tables(soup),
            "stats": self._extract_stats(soup),
        }

    def _extract_tables(self, soup: BeautifulSoup) -> list[dict]:
        """Extract tables from the page."""
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

    def _extract_stats(self, soup: BeautifulSoup) -> list[dict]:
        """Extract statistics/counter elements common on project pages."""
        stats = []
        # Look for counter/stats sections
        for el in soup.find_all(
            class_=lambda c: c and any(
                kw in str(c).lower()
                for kw in ["stat", "counter", "number", "metric", "fact"]
            )
        ):
            stat = {
                "text": el.get_text(strip=True)[:200],
            }
            # Try to find a number
            for child in el.find_all(["span", "strong", "b", "h2", "h3"]):
                text = child.get_text(strip=True)
                if any(c.isdigit() for c in text):
                    stat["value"] = text
                    break
            stats.append(stat)
        return stats

    def _parse_page(self, soup: BeautifulSoup, url: str) -> list[dict]:
        """Parse datasets from a GenomeIndia page."""
        datasets = []

        # Look for sections about specific populations or datasets
        for section in soup.find_all(["section", "div", "article"]):
            headings = section.find_all(["h2", "h3", "h4"])
            for heading in headings:
                text = heading.get_text(strip=True)
                # Look for population/dataset-related headings
                keywords = [
                    "population", "genome", "dataset", "cohort",
                    "sample", "sequenc", "data", "biobank",
                ]
                if any(kw in text.lower() for kw in keywords) and len(text) > 10:
                    # Get the surrounding context
                    parent = heading.find_parent(["section", "div", "article"])
                    context = ""
                    if parent:
                        context = parent.get_text(strip=True)[:500]

                    datasets.append({
                        "name": text,
                        "source": self.source_name,
                        "institution_name": "GenomeIndia Consortium (IISc, Bengaluru)",
                        "source_url": url,
                        "data_type": "genomic",
                        "_context": context,
                    })

        # Look for tables with population/sample data
        for table_data in self._extract_tables(soup):
            headers_lower = [h.lower() for h in table_data.get("headers", [])]
            if any(
                kw in " ".join(headers_lower)
                for kw in ["population", "state", "sample", "ethnic"]
            ):
                for row in table_data.get("rows", []):
                    if isinstance(row, dict):
                        name_field = next(
                            (v for k, v in row.items() if "name" in k.lower() or "population" in k.lower()),
                            None,
                        )
                        if name_field:
                            datasets.append({
                                "name": f"GenomeIndia — {name_field}",
                                "source": self.source_name,
                                "institution_name": "GenomeIndia Consortium",
                                "source_url": url,
                                "data_type": "genomic",
                                "_raw_row": row,
                            })

        return datasets

    def _get_known_metadata(self) -> list[dict]:
        """
        Return known metadata about GenomeIndia datasets.

        GenomeIndia is well-documented in scientific literature.
        """
        return [
            {
                "name": "GenomeIndia — 10,000 Indian Genomes Reference Panel",
                "source": self.source_name,
                "institution_name": "Indian Institute of Science (IISc), Bengaluru + consortium",
                "state_of_collection": "Multi-state",
                "population_group": "Pan-Indian (diverse ethnic groups across India)",
                "data_type": "genomic",
                "disease_association": "Population reference panel",
                "sample_size": 10000,
                "access_type": "managed",
                "source_url": "https://genomeindia.org",
                "contact_researcher": "Prof. Partha P. Majumder, ISI Kolkata / NIBMG",
                "license_type": "DBT-funded — managed access",
            },
            {
                "name": "GenomeIndia — Indo-European Linguistic Group Genomes",
                "source": self.source_name,
                "institution_name": "GenomeIndia Consortium",
                "state_of_collection": "Multi-state (North and West India)",
                "population_group": "Indo-European speaking populations",
                "data_type": "genomic",
                "disease_association": "Population genetics reference",
                "access_type": "managed",
                "source_url": "https://genomeindia.org",
                "license_type": "DBT-funded — managed access",
            },
            {
                "name": "GenomeIndia — Tibeto-Burman Linguistic Group Genomes",
                "source": self.source_name,
                "institution_name": "GenomeIndia Consortium",
                "state_of_collection": "Multi-state (Northeast India)",
                "population_group": "Tibeto-Burman speaking populations",
                "data_type": "genomic",
                "disease_association": "Population genetics reference",
                "access_type": "managed",
                "source_url": "https://genomeindia.org",
                "license_type": "DBT-funded — managed access",
            },
        ]
