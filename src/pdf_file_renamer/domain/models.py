"""Domain models - core business entities."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Confidence level for filename suggestions."""

    VERY_HIGH = "very_high"  # DOI-backed metadata
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ERROR = "error"


@dataclass(frozen=True)
class DOIMetadata:
    """Metadata extracted from DOI lookup."""

    doi: str
    title: str | None = None
    authors: list[str] | None = None
    year: str | None = None
    journal: str | None = None
    publisher: str | None = None
    raw_bibtex: str | None = None

    @property
    def first_author(self) -> str | None:
        """Get the first author's last name."""
        if not self.authors or len(self.authors) == 0:
            return None
        # Extract last name from first author (handles "Last, First" or "First Last" formats)
        first = self.authors[0]
        if "," in first:
            return first.split(",")[0].strip()
        # Assume last word is last name
        parts = first.strip().split()
        return parts[-1] if parts else None


class FilenameResult(BaseModel):
    """Result of filename generation."""

    model_config = {"use_enum_values": True}

    filename: str = Field(description="Suggested filename without extension")
    confidence: ConfidenceLevel = Field(description="Confidence level of the suggestion")
    reasoning: str = Field(description="Explanation of why this filename was chosen")


@dataclass(frozen=True)
class PDFMetadata:
    """Metadata extracted from PDF."""

    title: str | None = None
    author: str | None = None
    subject: str | None = None
    keywords: str | None = None
    creator: str | None = None
    producer: str | None = None
    creation_date: str | None = None
    modification_date: str | None = None
    # Focused metadata extracted from document content
    header_text: str | None = None
    year_hints: list[str] | None = None
    email_hints: list[str] | None = None
    author_hints: list[str] | None = None

    def to_dict(self) -> dict[str, str | list[str] | None]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass(frozen=True)
class PDFContent:
    """Extracted content from PDF."""

    text: str
    metadata: PDFMetadata
    page_count: int
    doi_metadata: DOIMetadata | None = None


@dataclass
class FileRenameOperation:
    """Represents a file rename operation."""

    original_path: Path
    suggested_filename: str
    confidence: ConfidenceLevel
    reasoning: str
    text_excerpt: str
    metadata: PDFMetadata
    doi_metadata: DOIMetadata | None = None

    @property
    def new_filename(self) -> str:
        """Get the new filename with extension."""
        return f"{self.suggested_filename}.pdf"

    def create_new_path(self, output_dir: Path | None = None) -> Path:
        """Create the new path for the renamed file."""
        target_dir = output_dir if output_dir else self.original_path.parent
        return target_dir / self.new_filename
