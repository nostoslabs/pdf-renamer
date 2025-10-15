"""DOI extraction using pdf2doi library."""

import asyncio
import contextlib
import re
from difflib import SequenceMatcher
from pathlib import Path

import pdf2doi

from pdf_file_renamer.domain.models import DOIMetadata
from pdf_file_renamer.domain.ports import DOIExtractor


class PDF2DOIExtractor(DOIExtractor):
    """Extract DOI from PDF files using pdf2doi library."""

    def __init__(self, validate_match: bool = True, similarity_threshold: float = 0.3) -> None:
        """
        Initialize the PDF2DOI extractor.

        Args:
            validate_match: Whether to validate that DOI metadata matches PDF content
            similarity_threshold: Minimum similarity score (0-1) for title validation
        """
        # Suppress pdf2doi verbose output
        pdf2doi.config.set("verbose", False)
        self.validate_match = validate_match
        self.similarity_threshold = similarity_threshold

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

            doi_metadata = DOIMetadata(
                doi=identifier,
                title=title,
                authors=authors,
                year=year,
                journal=journal,
                publisher=publisher,
                raw_bibtex=validation_info if validation_info else None,
            )

            # Validate that the DOI metadata matches the PDF content
            if self.validate_match:
                # Extract first page text from PDF to check for title match
                pdf_text = await self._extract_pdf_first_page(pdf_path)
                if not self._validate_doi_matches_pdf(doi_metadata, pdf_text):
                    # DOI doesn't match - likely a citation DOI, not the paper's DOI
                    return None

            return doi_metadata

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

    async def _extract_pdf_first_page(self, pdf_path: Path) -> str:
        """
        Extract text from the first page of a PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Text from first page (empty string if extraction fails)
        """
        try:
            import fitz  # PyMuPDF

            loop = asyncio.get_event_loop()

            def extract() -> str:
                with fitz.open(pdf_path) as doc:
                    if len(doc) > 0:
                        return doc[0].get_text()
                return ""

            return await loop.run_in_executor(None, extract)
        except Exception:
            return ""

    def _validate_doi_matches_pdf(self, doi_metadata: DOIMetadata, pdf_text: str) -> bool:
        """
        Validate that DOI metadata matches the PDF content.

        This checks if the title from the DOI metadata appears in the PDF text
        (particularly the first page, where the title should be).

        Args:
            doi_metadata: DOI metadata to validate
            pdf_text: Text from PDF first page (not full document!)

        Returns:
            True if metadata appears to match PDF, False otherwise
        """
        if not doi_metadata.title or not pdf_text:
            # If we can't validate, assume it's valid (fail open)
            return True

        # Normalize text for comparison
        pdf_text_lower = pdf_text.lower()
        title_lower = doi_metadata.title.lower()

        # Check if the full title appears in the PDF text
        if title_lower in pdf_text_lower:
            return True

        # Check similarity using SequenceMatcher on first ~300 chars (title area)
        # Most paper titles appear in the first few hundred characters
        title_area = pdf_text_lower[:300]
        similarity = SequenceMatcher(None, title_lower, title_area).ratio()

        if similarity >= self.similarity_threshold:
            return True

        # Check if significant words from title appear in the title area ONLY
        # This prevents matching citation DOIs from the references section
        title_words = self._extract_significant_words(title_lower)
        if not title_words:
            return True  # Can't validate, fail open

        # Require at least 70% of significant words to appear in the title area
        matches = sum(1 for word in title_words if word in title_area)
        match_ratio = matches / len(title_words)

        return match_ratio >= 0.7

    def _extract_significant_words(self, text: str) -> list[str]:
        """
        Extract significant words from text (removing common words).

        Args:
            text: Input text

        Returns:
            List of significant words
        """
        # Common words to skip
        stop_words = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
            "been",
            "be",
            "this",
            "that",
            "these",
            "those",
        }

        # Extract words (alphanumeric only)
        words = re.findall(r"\b\w+\b", text.lower())

        # Filter stop words and short words
        return [w for w in words if w not in stop_words and len(w) > 3]
