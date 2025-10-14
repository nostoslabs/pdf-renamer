"""DOI extraction using pdf2doi library."""

import asyncio
import contextlib
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
            result = await loop.run_in_executor(None, pdf2doi.pdf2doi, str(pdf_path))

            # pdf2doi returns a dict (not a list)
            if not result or not isinstance(result, dict):
                return None

            # Check if DOI was found
            identifier = result.get("identifier")
            if not identifier:
                return None

            identifier_type = result.get("identifier_type", "")
            if identifier_type.lower() not in ("doi", "arxiv"):
                return None

            # Extract metadata from validation_info (JSON string from CrossRef API)
            validation_info = result.get("validation_info", "")

            # Parse JSON metadata
            import json

            metadata = {}
            if validation_info:
                with contextlib.suppress(json.JSONDecodeError):
                    metadata = json.loads(validation_info)

            # Extract title
            title = metadata.get("title")

            # Extract authors (list of dicts with 'given' and 'family' fields)
            authors: list[str] | None = None
            if "author" in metadata:
                author_list = metadata["author"]
                author_names: list[str] = []
                for author in author_list:
                    if isinstance(author, dict):
                        family = author.get("family", "")
                        given = author.get("given", "")
                        if family:
                            full_name = f"{given} {family}".strip() if given else family
                            author_names.append(full_name)
                if author_names:
                    authors = author_names

            # Extract year from published-online or published
            year = None
            for date_field in ["published-online", "published", "created"]:
                if date_field in metadata and "date-parts" in metadata[date_field]:
                    date_parts = metadata[date_field]["date-parts"]
                    if date_parts and len(date_parts) > 0 and len(date_parts[0]) > 0:
                        year = str(date_parts[0][0])
                        break

            # Extract journal (container-title)
            journal = metadata.get("container-title")

            # Extract publisher
            publisher = metadata.get("publisher")

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
