"""DOI extraction using pdf2doi library."""

import asyncio
import re
from pathlib import Path

import pdf2doi

from pdf_file_renamer.domain.models import DOIMetadata
from pdf_file_renamer.domain.ports import DOIExtractor


class PDF2DOIExtractor(DOIExtractor):
    """Extract DOI from PDF files using pdf2doi library."""

    def __init__(self) -> None:
        """Initialize the PDF2DOI extractor."""
        # Suppress pdf2doi verbose output
        pdf2doi.config.set("verbose", False)

    async def extract_doi(self, pdf_path: Path) -> DOIMetadata | None:
        """
        Extract DOI from PDF and fetch metadata.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            DOIMetadata if DOI found and validated, None otherwise
        """
        try:
            # Run pdf2doi in executor to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, pdf2doi.pdf2doi, str(pdf_path)
            )

            if not results or len(results) == 0:
                return None

            # Get the first result
            result = results[0]

            # Check if DOI was found
            identifier = result.get("identifier")
            if not identifier:
                return None

            identifier_type = result.get("identifier_type", "")
            if identifier_type.lower() not in ("doi", "arxiv"):
                return None

            # Extract metadata from validation_info (bibtex)
            validation_info = result.get("validation_info", "")

            # Parse bibtex for metadata
            title = self._extract_bibtex_field(validation_info, "title")
            authors = self._extract_bibtex_authors(validation_info)
            year = self._extract_bibtex_field(validation_info, "year")
            journal = self._extract_bibtex_field(validation_info, "journal")
            publisher = self._extract_bibtex_field(validation_info, "publisher")

            return DOIMetadata(
                doi=identifier,
                title=title,
                authors=authors,
                year=year,
                journal=journal,
                publisher=publisher,
                raw_bibtex=validation_info if validation_info else None,
            )

        except Exception:
            # Silently fail - DOI extraction is opportunistic
            return None

    def _extract_bibtex_field(self, bibtex: str, field: str) -> str | None:
        """
        Extract a field from bibtex string.

        Args:
            bibtex: Bibtex string
            field: Field name to extract

        Returns:
            Field value or None
        """
        if not bibtex:
            return None

        # Match field = {value} or field = "value"
        pattern = rf"{field}\s*=\s*[{{\"](.*?)[\}}\"](,|\n|$)"
        match = re.search(pattern, bibtex, re.IGNORECASE)

        if match:
            return match.group(1).strip()

        return None

    def _extract_bibtex_authors(self, bibtex: str) -> list[str] | None:
        """
        Extract authors from bibtex string.

        Args:
            bibtex: Bibtex string

        Returns:
            List of author names or None
        """
        if not bibtex:
            return None

        # Match author = {Name1 and Name2 and Name3}
        pattern = r"author\s*=\s*[{\"](.*?)[\}\"](,|\n|$)"
        match = re.search(pattern, bibtex, re.IGNORECASE)

        if not match:
            return None

        authors_str = match.group(1).strip()

        # Split by "and" and clean up
        authors = [
            author.strip()
            for author in re.split(r"\s+and\s+", authors_str, flags=re.IGNORECASE)
            if author.strip()
        ]

        return authors if authors else None
