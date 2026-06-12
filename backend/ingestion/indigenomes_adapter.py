"""
BioNexus India V1 — IndiGenomes Adapter

Fetches dataset metadata from the IndiGenomes portal
(https://indigenomes.igib.res.in).

IndiGenomes is a genome aggregation resource from CSIR-IGIB that provides
allele frequencies and variant data for Indian populations. It primarily
serves as a variant browser rather than a dataset catalog, so this adapter
scrapes structured information from the portal's public pages.

Source: CSIR-Institute of Genomics and Integrative Biology (IGIB), Delhi
"""

import logging
from bs4 import BeautifulSoup

from ingestion.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class IndiGenomesAdapter(BaseAdapter):
    """Adapter for the IndiGenomes portal (CSIR-IGIB)."""

    source_name = "indigenomes"
    base_url = "https://indigenomes.igib.res.in"

    async def fetch_datasets(self) -> list[dict]:
        """
        Fetch dataset metadata from IndiGenomes.

        IndiGenomes is a variant browser for Indian genomes. We scrape
        the main pages to extract information about the datasets that
        underlie the browser (WGS data, population panels, etc.).
        """
        datasets = []

        try:
            # Fetch the main page
            response = await self._fetch_url(self.base_url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")

                # Extract dataset information from the main page
                # IndiGenomes typically presents information about their
                # genome dataset in structured sections
                page_data = {
                    "title": self._extract_title(soup),
                    "description": self._extract_description(soup),
                    "tables": self._extract_tables(soup),
                    "links": self._extract_links(soup),
                    "text_content": self._extract_text_blocks(soup),
                }

                self._store_raw_response(page_data, suffix="main_page")

                # Parse the main IndiGenomes dataset entry
                main_dataset = self._parse_main_dataset(page_data)
                if main_dataset:
                    datasets.append(main_dataset)

                # Try to find additional dataset/population pages
                sub_pages = self._find_dataset_pages(soup)
                for page_url in sub_pages:
                    try:
                        sub_response = await self._fetch_url(page_url)
                        if sub_response.status_code == 200:
                            sub_soup = BeautifulSoup(sub_response.text, "lxml")
                            sub_data = {
                                "url": page_url,
                                "title": self._extract_title(sub_soup),
                                "description": self._extract_description(sub_soup),
                                "tables": self._extract_tables(sub_soup),
                                "text_content": self._extract_text_blocks(sub_soup),
                            }
                            self._store_raw_response(sub_data, suffix="sub_page")

                            sub_dataset = self._parse_sub_page(sub_data)
                            if sub_dataset:
                                datasets.append(sub_dataset)
                    except Exception as e:
                        logger.warning(
                            f"Failed to fetch sub-page {page_url}: {e}"
                        )
                        continue

            else:
                logger.warning(
                    f"IndiGenomes returned status {response.status_code}"
                )

        except Exception as e:
            logger.error(f"Error fetching IndiGenomes: {e}", exc_info=True)
            # Return whatever we have so far — never fail completely
            # If we got nothing from live scraping, return a known metadata entry
            if not datasets:
                datasets.append(self._get_known_metadata())

        # If scraping yielded nothing, use known metadata
        if not datasets:
            datasets.append(self._get_known_metadata())
            logger.info(
                "Using known metadata for IndiGenomes "
                "(live scraping yielded no structured data)"
            )

        self._store_raw_response(datasets, suffix="final_output")
        return datasets

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        """Extract page title."""
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else None

    def _extract_description(self, soup: BeautifulSoup) -> str | None:
        """Extract meta description or first paragraph."""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"]
        first_p = soup.find("p")
        return first_p.get_text(strip=True) if first_p else None

    def _extract_tables(self, soup: BeautifulSoup) -> list[dict]:
        """Extract all HTML tables as structured data."""
        tables = []
        for table in soup.find_all("table"):
            rows = []
            headers = []
            for th in table.find_all("th"):
                headers.append(th.get_text(strip=True))
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                if cells:
                    if headers:
                        row_dict = dict(zip(headers, cells))
                        rows.append(row_dict)
                    else:
                        rows.append(cells)
            if rows:
                tables.append({"headers": headers, "rows": rows})
        return tables

    def _extract_links(self, soup: BeautifulSoup) -> list[dict]:
        """Extract all links with text and href."""
        links = []
        for a in soup.find_all("a", href=True):
            links.append({
                "text": a.get_text(strip=True),
                "href": a["href"],
            })
        return links

    def _extract_text_blocks(self, soup: BeautifulSoup) -> list[str]:
        """Extract meaningful text blocks from the page."""
        blocks = []
        for tag in soup.find_all(["p", "div", "section", "article"]):
            text = tag.get_text(strip=True)
            if len(text) > 50:  # Skip trivial elements
                blocks.append(text[:500])  # Cap length
        return blocks[:20]  # Limit number of blocks

    def _find_dataset_pages(self, soup: BeautifulSoup) -> list[str]:
        """Find links to sub-pages that might contain dataset info."""
        dataset_pages = []
        keywords = ["data", "dataset", "population", "sample", "download", "about"]

        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True).lower()

            if any(kw in text for kw in keywords) or any(
                kw in href.lower() for kw in keywords
            ):
                # Resolve relative URLs
                if href.startswith("/"):
                    full_url = f"{self.base_url}{href}"
                elif href.startswith("http"):
                    full_url = href
                else:
                    full_url = f"{self.base_url}/{href}"

                # Only follow links within the same domain
                if "indigenomes" in full_url and full_url not in dataset_pages:
                    dataset_pages.append(full_url)

        return dataset_pages[:5]  # Limit to avoid excessive crawling

    def _parse_main_dataset(self, page_data: dict) -> dict | None:
        """Parse the main IndiGenomes dataset from scraped page data."""
        title = page_data.get("title", "")
        description = page_data.get("description", "")

        if not title and not description:
            return None

        return {
            "name": title or "IndiGenomes — Indian Genome Variation Database",
            "source": self.source_name,
            "institution_name": "CSIR-Institute of Genomics and Integrative Biology (IGIB), Delhi",
            "description": description,
            "source_url": self.base_url,
            "data_type": "genomic",
            "population_group": "Pan-Indian",
            "state_of_collection": "Multi-state",
            "access_type": "managed",
            "_raw_tables": page_data.get("tables", []),
        }

    def _parse_sub_page(self, sub_data: dict) -> dict | None:
        """Parse a sub-page into a dataset record if it contains useful info."""
        title = sub_data.get("title", "")
        if not title or len(title) < 10:
            return None

        return {
            "name": title,
            "source": self.source_name,
            "institution_name": "CSIR-IGIB",
            "source_url": sub_data.get("url", self.base_url),
            "data_type": "genomic",
            "_raw_tables": sub_data.get("tables", []),
        }

    def _get_known_metadata(self) -> dict:
        """
        Return known metadata about IndiGenomes.

        This is a fallback when live scraping fails. IndiGenomes is a
        well-documented resource — we know its basic metadata from
        published literature.
        """
        return {
            "name": "IndiGenomes — Whole Genome Sequences of 1029 Indian Individuals",
            "source": self.source_name,
            "institution_name": "CSIR-Institute of Genomics and Integrative Biology (IGIB), Delhi",
            "state_of_collection": "Multi-state",
            "population_group": "Pan-Indian (27 ethnic groups)",
            "data_type": "genomic",
            "disease_association": "Population reference panel (healthy individuals)",
            "sample_size": 1029,
            "access_type": "managed",
            "source_url": "https://indigenomes.igib.res.in",
            "contact_researcher": "Dr. Sridhar Sivasubbu, CSIR-IGIB",
            "license_type": "Academic use only",
            "doi": "10.1093/nar/gkz1037",
        }
