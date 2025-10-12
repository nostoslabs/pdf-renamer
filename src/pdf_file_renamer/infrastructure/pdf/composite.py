"""Composite PDF extractor that tries multiple strategies."""

from pathlib import Path

from pdf_file_renamer.domain.models import PDFContent
from pdf_file_renamer.domain.ports import PDFExtractor


class CompositePDFExtractor(PDFExtractor):
    """
    Composite PDF extractor that tries multiple extractors in sequence.

    This implements the Chain of Responsibility pattern with fallback strategy.
    """

    def __init__(self, extractors: list[PDFExtractor]) -> None:
        """
        Initialize the composite extractor.

        Args:
            extractors: List of extractors to try in order
        """
        if not extractors:
            msg = "At least one extractor must be provided"
            raise ValueError(msg)
        self.extractors = extractors

    async def extract(self, pdf_path: Path) -> PDFContent:
        """
        Try extractors in sequence until one succeeds.

        Args:
            pdf_path: Path to PDF file

        Returns:
            PDFContent from first successful extractor

        Raises:
            RuntimeError: If all extractors fail
        """
        errors: list[str] = []

        for extractor in self.extractors:
            try:
                content = await extractor.extract(pdf_path)
                # Only accept if we got meaningful text
                if len(content.text.strip()) > 100:
                    return content
                errors.append(f"{extractor.__class__.__name__}: Insufficient text extracted")
            except Exception as e:
                errors.append(f"{extractor.__class__.__name__}: {e}")
                continue

        # All extractors failed
        error_msg = "; ".join(errors)
        msg = f"All PDF extractors failed for {pdf_path}: {error_msg}"
        raise RuntimeError(msg)
