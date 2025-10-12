"""Tests for domain models."""

from pathlib import Path

from pdf_file_renamer.domain.models import (
    ConfidenceLevel,
    FilenameResult,
    FileRenameOperation,
    PDFContent,
    PDFMetadata,
)


class TestPDFMetadata:
    """Tests for PDFMetadata."""

    def test_to_dict_excludes_none(self) -> None:
        """Test that to_dict excludes None values."""
        metadata = PDFMetadata(title="Test", author=None)
        result = metadata.to_dict()
        assert "title" in result
        assert "author" not in result

    def test_to_dict_includes_all_values(self) -> None:
        """Test that to_dict includes all non-None values."""
        metadata = PDFMetadata(
            title="Test Title",
            author="Test Author",
            year_hints=["2020", "2021"],
        )
        result = metadata.to_dict()
        assert result["title"] == "Test Title"
        assert result["author"] == "Test Author"
        assert result["year_hints"] == ["2020", "2021"]


class TestPDFContent:
    """Tests for PDFContent."""

    def test_creation(self) -> None:
        """Test PDFContent creation."""
        metadata = PDFMetadata(title="Test")
        content = PDFContent(text="Sample text", metadata=metadata, page_count=10)
        assert content.text == "Sample text"
        assert content.metadata.title == "Test"
        assert content.page_count == 10


class TestFilenameResult:
    """Tests for FilenameResult."""

    def test_creation_with_enum(self) -> None:
        """Test creation with enum."""
        result = FilenameResult(
            filename="test-file",
            confidence=ConfidenceLevel.HIGH,
            reasoning="Clear title and author",
        )
        assert result.filename == "test-file"
        assert result.confidence == ConfidenceLevel.HIGH

    def test_creation_with_string(self) -> None:
        """Test creation with string confidence."""
        result = FilenameResult(
            filename="test-file",
            confidence="high",  # type: ignore[arg-type]
            reasoning="Clear title",
        )
        assert result.confidence == ConfidenceLevel.HIGH


class TestFileRenameOperation:
    """Tests for FileRenameOperation."""

    def test_new_filename(self) -> None:
        """Test new_filename property."""
        op = FileRenameOperation(
            original_path=Path("/tmp/old.pdf"),
            suggested_filename="new-name",
            confidence=ConfidenceLevel.HIGH,
            reasoning="Test",
            text_excerpt="Sample",
            metadata=PDFMetadata(),
        )
        assert op.new_filename == "new-name.pdf"

    def test_create_new_path_same_dir(self) -> None:
        """Test create_new_path without output dir."""
        op = FileRenameOperation(
            original_path=Path("/tmp/old.pdf"),
            suggested_filename="new-name",
            confidence=ConfidenceLevel.HIGH,
            reasoning="Test",
            text_excerpt="Sample",
            metadata=PDFMetadata(),
        )
        new_path = op.create_new_path()
        assert new_path == Path("/tmp/new-name.pdf")

    def test_create_new_path_different_dir(self) -> None:
        """Test create_new_path with output dir."""
        op = FileRenameOperation(
            original_path=Path("/tmp/old.pdf"),
            suggested_filename="new-name",
            confidence=ConfidenceLevel.HIGH,
            reasoning="Test",
            text_excerpt="Sample",
            metadata=PDFMetadata(),
        )
        new_path = op.create_new_path(Path("/output"))
        assert new_path == Path("/output/new-name.pdf")
