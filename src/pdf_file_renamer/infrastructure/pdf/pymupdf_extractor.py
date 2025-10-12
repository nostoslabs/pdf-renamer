"""PyMuPDF-based PDF extractor with metadata support and OCR fallback."""

import re
from pathlib import Path

import pymupdf

from pdf_file_renamer.domain.models import PDFContent, PDFMetadata
from pdf_file_renamer.domain.ports import PDFExtractor


class PyMuPDFExtractor(PDFExtractor):
    """PDF extractor using PyMuPDF with metadata and OCR support."""

    def __init__(self, max_pages: int = 5, max_chars: int = 8000, enable_ocr: bool = True) -> None:
        """
        Initialize the PyMuPDF extractor.

        Args:
            max_pages: Maximum pages to extract
            max_chars: Maximum characters to extract
            enable_ocr: Enable OCR for scanned PDFs
        """
        self.max_pages = max_pages
        self.max_chars = max_chars
        self.enable_ocr = enable_ocr

    async def extract(self, pdf_path: Path) -> PDFContent:
        """
        Extract text and metadata from PDF using PyMuPDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            PDFContent with extracted text and metadata

        Raises:
            RuntimeError: If extraction fails
        """
        try:
            doc = pymupdf.open(pdf_path)
            text_parts: list[str] = []
            total_chars = 0

            for page_num in range(min(self.max_pages, len(doc))):
                page = doc[page_num]
                page_text = page.get_text()

                # Add page text until we hit the character limit
                remaining_chars = self.max_chars - total_chars
                if remaining_chars <= 0:
                    break

                text_parts.append(page_text[:remaining_chars])
                total_chars += len(page_text)

            extracted_text = "\n".join(text_parts).strip()

            # If very little text and OCR enabled, try OCR
            if len(extracted_text) < 200 and self.enable_ocr:
                extracted_text = await self._extract_with_ocr(pdf_path, doc)

            # Extract metadata
            metadata = await self._extract_metadata(pdf_path, doc, extracted_text)

            page_count = len(doc)
            doc.close()

            return PDFContent(text=extracted_text, metadata=metadata, page_count=page_count)

        except Exception as e:
            msg = f"Failed to extract text from {pdf_path} using PyMuPDF: {e}"
            raise RuntimeError(msg) from e

    async def _extract_with_ocr(self, pdf_path: Path, doc: pymupdf.Document) -> str:
        """
        Extract text using OCR for scanned PDFs.

        Args:
            pdf_path: Path to PDF file
            doc: PyMuPDF document

        Returns:
            Extracted text
        """
        text_parts: list[str] = []
        total_chars = 0

        for page_num in range(min(self.max_pages, len(doc))):
            page = doc[page_num]

            try:
                # Try OCR with Tesseract (if available)
                tp = page.get_textpage(flags=0)
                page_text = tp.extractText()

                # If still no text, try with flags
                if not page_text or len(page_text.strip()) < 50:
                    page_text = page.get_text("text", flags=pymupdf.TEXT_PRESERVE_WHITESPACE)
            except Exception:
                # If OCR fails, get whatever text is available
                page_text = page.get_text()

            # Add page text until we hit the character limit
            remaining_chars = self.max_chars - total_chars
            if remaining_chars <= 0:
                break

            text_parts.append(page_text[:remaining_chars])
            total_chars += len(page_text)

        return "\n".join(text_parts).strip()

    async def _extract_metadata(
        self, pdf_path: Path, doc: pymupdf.Document, text: str
    ) -> PDFMetadata:
        """
        Extract metadata from PDF.

        Args:
            pdf_path: Path to PDF file
            doc: PyMuPDF document
            text: Extracted text content

        Returns:
            PDFMetadata
        """
        # Get PDF metadata
        meta = doc.metadata or {}

        # Extract focused metadata from text
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
            title=meta.get("title"),
            author=meta.get("author"),
            subject=meta.get("subject"),
            keywords=meta.get("keywords"),
            creator=meta.get("creator"),
            producer=meta.get("producer"),
            creation_date=meta.get("creationDate"),
            modification_date=meta.get("modDate"),
            header_text=header_text,
            year_hints=years[:3] if years else None,
            email_hints=emails[:3] if emails else None,
            author_hints=author_hints[:2] if author_hints else None,
        )
