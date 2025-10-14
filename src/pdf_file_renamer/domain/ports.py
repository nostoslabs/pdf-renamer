"""Domain ports - interfaces for external dependencies (Dependency Inversion Principle)."""

from abc import ABC, abstractmethod
from pathlib import Path

from pdf_file_renamer.domain.models import DOIMetadata, FilenameResult, PDFContent


class DOIExtractor(ABC):
    """Interface for DOI extraction and metadata lookup."""

    @abstractmethod
    async def extract_doi(self, pdf_path: Path) -> DOIMetadata | None:
        """
        Extract DOI from PDF and fetch metadata.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            DOIMetadata if DOI found and validated, None otherwise
        """
        pass


class PDFExtractor(ABC):
    """Interface for PDF text extraction."""

    @abstractmethod
    async def extract(self, pdf_path: Path) -> PDFContent:
        """
        Extract text and metadata from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            PDFContent with extracted text and metadata

        Raises:
            RuntimeError: If extraction fails
        """
        pass


class LLMProvider(ABC):
    """Interface for LLM providers."""

    @abstractmethod
    async def generate_filename(
        self,
        original_filename: str,
        text_excerpt: str,
        metadata_dict: dict[str, str | list[str] | None],
    ) -> FilenameResult:
        """
        Generate a filename suggestion using an LLM.

        Args:
            original_filename: Current filename
            text_excerpt: Extracted text from PDF
            metadata_dict: PDF metadata dictionary

        Returns:
            FilenameResult with suggestion and confidence

        Raises:
            RuntimeError: If generation fails
        """
        pass


class FilenameGenerator(ABC):
    """Interface for filename generation service."""

    @abstractmethod
    async def generate(self, original_filename: str, content: PDFContent) -> FilenameResult:
        """
        Generate a filename suggestion based on PDF content.

        Args:
            original_filename: Current filename
            content: Extracted PDF content

        Returns:
            FilenameResult with suggestion
        """
        pass

    @abstractmethod
    def sanitize(self, filename: str) -> str:
        """
        Sanitize a filename to be filesystem-safe.

        Args:
            filename: Raw filename

        Returns:
            Sanitized filename
        """
        pass


class FileRenamer(ABC):
    """Interface for file renaming operations."""

    @abstractmethod
    async def rename(self, original_path: Path, new_path: Path, dry_run: bool = True) -> bool:
        """
        Rename a file.

        Args:
            original_path: Original file path
            new_path: New file path
            dry_run: If True, don't actually rename

        Returns:
            True if successful

        Raises:
            RuntimeError: If rename fails
        """
        pass
