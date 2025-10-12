"""Docling-based PDF extractor for structure-aware text extraction."""

import re
from pathlib import Path

from docling_core.types.doc.page import TextCellUnit
from docling_parse.pdf_parser import DoclingPdfParser

from pdf_file_renamer.domain.models import PDFContent, PDFMetadata
from pdf_file_renamer.domain.ports import PDFExtractor


class DoclingPDFExtractor(PDFExtractor):
    """PDF extractor using docling-parse for better structure-aware extraction."""

    def __init__(self, max_pages: int = 5, max_chars: int = 8000) -> None:
        """
        Initialize the Docling PDF extractor.

        Args:
            max_pages: Maximum pages to extract
            max_chars: Maximum characters to extract
        """
        self.max_pages = max_pages
        self.max_chars = max_chars
        self._parser = DoclingPdfParser()

    async def extract(self, pdf_path: Path) -> PDFContent:
        """
        Extract text and metadata from PDF using docling-parse.

        Args:
            pdf_path: Path to PDF file

        Returns:
            PDFContent with extracted text and metadata

        Raises:
            RuntimeError: If extraction fails
        """
        try:
            pdf_doc = self._parser.load(path_or_stream=str(pdf_path))

            text_parts: list[str] = []
            total_chars = 0
            page_count = 0

            for page_no, pred_page in pdf_doc.iterate_pages():
                page_count += 1
                if page_no >= self.max_pages:
                    break

                # Extract text at line level for better structure preservation
                page_lines: list[str] = []
                for line in pred_page.iterate_cells(unit_type=TextCellUnit.LINE):
                    page_lines.append(line.text)

                page_text = "\n".join(page_lines)

                # Add page text until we hit the character limit
                remaining_chars = self.max_chars - total_chars
                if remaining_chars <= 0:
                    break

                text_parts.append(page_text[:remaining_chars])
                total_chars += len(page_text)

            extracted_text = "\n".join(text_parts).strip()

            # Extract metadata using separate method
            metadata = await self._extract_metadata(pdf_path, extracted_text)

            return PDFContent(text=extracted_text, metadata=metadata, page_count=page_count)

        except Exception as e:
            msg = f"Failed to extract text from {pdf_path} using docling-parse: {e}"
            raise RuntimeError(msg) from e

    async def _extract_metadata(self, pdf_path: Path, text: str) -> PDFMetadata:
        """
        Extract metadata from PDF.

        Args:
            pdf_path: Path to PDF file
            text: Extracted text content

        Returns:
            PDFMetadata
        """
        # Note: docling-parse doesn't provide document-level metadata
        # So we extract focused metadata from the text content
        header_text = text[:500] if text else ""

        # Extract year hints
        year_pattern = r"\b(19\d{2}|20\d{2})\b"
        years = re.findall(year_pattern, header_text)

        # Extract email hints
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        emails = re.findall(email_pattern, text[:2000])

        # Look for author indicators
        author_indicators = ["by ", "author:", "authors:", "written by"]
        author_hints: list[str] = []
        text_lower = text[:2000].lower()
        for indicator in author_indicators:
            if indicator in text_lower:
                idx = text_lower.index(indicator)
                author_hints.append(text[idx : idx + 100])

        return PDFMetadata(
            header_text=header_text,
            year_hints=years[:3] if years else None,
            email_hints=emails[:3] if emails else None,
            author_hints=author_hints[:2] if author_hints else None,
        )
