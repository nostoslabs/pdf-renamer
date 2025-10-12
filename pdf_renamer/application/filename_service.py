"""Filename generation service - coordinates PDF extraction and LLM generation."""

import re

from pdf_renamer.domain.models import FilenameResult, PDFContent
from pdf_renamer.domain.ports import FilenameGenerator, LLMProvider


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
