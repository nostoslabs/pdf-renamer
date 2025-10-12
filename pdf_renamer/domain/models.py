"""Domain models - core business entities."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Confidence level for filename suggestions."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ERROR = "error"


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


@dataclass
class FileRenameOperation:
    """Represents a file rename operation."""

    original_path: Path
    suggested_filename: str
    confidence: ConfidenceLevel
    reasoning: str
    text_excerpt: str
    metadata: PDFMetadata

    @property
    def new_filename(self) -> str:
        """Get the new filename with extension."""
        return f"{self.suggested_filename}.pdf"

    def create_new_path(self, output_dir: Path | None = None) -> Path:
        """Create the new path for the renamed file."""
        target_dir = output_dir if output_dir else self.original_path.parent
        return target_dir / self.new_filename
