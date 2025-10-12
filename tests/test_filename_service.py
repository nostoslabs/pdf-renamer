"""Tests for filename service."""

import pytest

from pdf_file_renamer.application.filename_service import FilenameService
from pdf_file_renamer.domain.models import (
    ConfidenceLevel,
    FilenameResult,
    PDFContent,
    PDFMetadata,
)
from pdf_file_renamer.domain.ports import LLMProvider


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, result: FilenameResult) -> None:
        self.result = result
        self.calls: list[dict] = []

    async def generate_filename(
        self,
        original_filename: str,
        text_excerpt: str,
        metadata_dict: dict[str, str | list[str] | None],
    ) -> FilenameResult:
        """Mock generate_filename."""
        self.calls.append(
            {
                "original_filename": original_filename,
                "text_excerpt": text_excerpt,
                "metadata_dict": metadata_dict,
            }
        )
        return self.result


class TestFilenameService:
    """Tests for FilenameService."""

    @pytest.mark.asyncio
    async def test_generate(self) -> None:
        """Test basic filename generation."""
        mock_result = FilenameResult(
            filename="Smith-Neural-Networks-2020",
            confidence=ConfidenceLevel.HIGH,
            reasoning="Clear title and author",
        )
        mock_llm = MockLLMProvider(mock_result)
        service = FilenameService(mock_llm)

        content = PDFContent(
            text="Sample text",
            metadata=PDFMetadata(title="Neural Networks"),
            page_count=10,
        )

        result = await service.generate("old.pdf", content)

        assert result.filename == "Smith-Neural-Networks-2020"
        assert result.confidence == ConfidenceLevel.HIGH
        assert len(mock_llm.calls) == 1

    @pytest.mark.asyncio
    async def test_generate_sanitizes_filename(self) -> None:
        """Test that filenames are sanitized."""
        mock_result = FilenameResult(
            filename="Smith: Neural/Networks*2020",
            confidence=ConfidenceLevel.HIGH,
            reasoning="Test",
        )
        mock_llm = MockLLMProvider(mock_result)
        service = FilenameService(mock_llm)

        content = PDFContent(text="Sample", metadata=PDFMetadata(), page_count=1)

        result = await service.generate("old.pdf", content)

        # Should remove invalid characters
        assert ":" not in result.filename
        assert "/" not in result.filename
        assert "*" not in result.filename

    def test_sanitize(self) -> None:
        """Test filename sanitization."""
        service = FilenameService(
            MockLLMProvider(
                FilenameResult(filename="", confidence=ConfidenceLevel.HIGH, reasoning="")
            )
        )

        # Test invalid characters
        assert service.sanitize("test:file") == "testfile"
        assert service.sanitize("test/file") == "testfile"
        assert service.sanitize("test|file") == "testfile"

        # Test spaces and hyphens
        assert service.sanitize("test  file") == "test-file"
        assert service.sanitize("test--file") == "test-file"

        # Test leading/trailing hyphens
        assert service.sanitize("-test-") == "test"

        # Test length limit
        long_name = "a" * 150
        result = service.sanitize(long_name)
        assert len(result) <= 100
