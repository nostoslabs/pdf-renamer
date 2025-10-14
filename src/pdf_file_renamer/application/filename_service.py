"""Filename generation service - coordinates PDF extraction and LLM generation."""

import re

from pdf_file_renamer.domain.models import ConfidenceLevel, FilenameResult, PDFContent
from pdf_file_renamer.domain.ports import FilenameGenerator, LLMProvider


class FilenameService(FilenameGenerator):
    """Service for generating filenames from PDF content."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        """
        Initialize the filename service.

        Args:
            llm_provider: LLM provider for filename generation
        """
        self.llm_provider = llm_provider

    async def generate(self, original_filename: str, content: PDFContent) -> FilenameResult:
        """
        Generate a filename suggestion based on PDF content.

        Args:
            original_filename: Current filename
            content: Extracted PDF content

        Returns:
            FilenameResult with suggestion
        """
        # If DOI metadata is available, use it directly for high-confidence naming
        if content.doi_metadata:
            return self._generate_from_doi(content)

        # Otherwise, fall back to LLM-based generation
        # Convert metadata to dictionary
        metadata_dict = content.metadata.to_dict()

        # Generate filename using LLM
        result = await self.llm_provider.generate_filename(
            original_filename=original_filename,
            text_excerpt=content.text,
            metadata_dict=metadata_dict,
        )

        # Sanitize the generated filename
        result.filename = self.sanitize(result.filename)

        return result

    def _generate_from_doi(self, content: PDFContent) -> FilenameResult:
        """
        Generate filename directly from DOI metadata.

        Args:
            content: PDF content with DOI metadata

        Returns:
            FilenameResult with very high confidence
        """
        doi_meta = content.doi_metadata
        if not doi_meta:
            msg = "DOI metadata not available"
            raise ValueError(msg)

        # Extract components for filename
        author = doi_meta.first_author or "Unknown"

        # Get title and clean it
        title = doi_meta.title or "Document"
        # Extract key words from title (remove common words)
        title_words = self._extract_key_words(title)

        year = doi_meta.year or ""

        # Build filename: Author-KeyWords-Year
        parts = [author]
        if title_words:
            parts.append(title_words)
        if year:
            parts.append(year)

        filename = "-".join(parts)
        filename = self.sanitize(filename)

        return FilenameResult(
            filename=filename,
            confidence=ConfidenceLevel.VERY_HIGH,
            reasoning=f"Filename generated from DOI metadata (DOI: {doi_meta.doi}). "
            f"Author: {author}, Year: {year}",
        )

    def _extract_key_words(self, title: str, max_words: int = 6) -> str:
        """
        Extract key words from title, removing common words.

        Args:
            title: Paper title
            max_words: Maximum number of words to include

        Returns:
            Hyphenated key words
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

        # Clean and split title
        words = re.sub(r"[^\w\s-]", " ", title.lower()).split()

        # Filter stop words and keep significant words
        key_words = [w for w in words if w not in stop_words and len(w) > 2]

        # Limit to max_words
        key_words = key_words[:max_words]

        # Capitalize first letter of each word
        key_words = [w.capitalize() for w in key_words]

        return "-".join(key_words)

    def sanitize(self, filename: str) -> str:
        """
        Sanitize a filename to be filesystem-safe.

        Args:
            filename: Raw filename

        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', "", filename)

        # Replace multiple spaces/hyphens with single hyphen
        filename = re.sub(r"[\s\-]+", "-", filename)

        # Remove leading/trailing hyphens
        filename = filename.strip("-")

        # Limit length
        if len(filename) > 100:
            filename = filename[:100].rstrip("-")

        return filename
