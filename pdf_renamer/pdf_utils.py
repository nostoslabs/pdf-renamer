"""Utility functions for extracting text from PDF files."""

import pymupdf
import sys
import re
from pathlib import Path
from docling_parse.pdf_parser import DoclingPdfParser
from docling_core.types.doc.page import TextCellUnit


def extract_pdf_text(pdf_path: Path, max_pages: int = 5, max_chars: int = 8000) -> str:
    """
    Extract text from the first few pages of a PDF using docling-parse.
    Falls back to PyMuPDF if docling-parse fails, with OCR support for scanned PDFs.

    Reduced defaults for faster processing - first 5 pages with 8000 chars is usually
    sufficient for filename generation (title, author, abstract typically on first 2 pages).

    Args:
        pdf_path: Path to the PDF file
        max_pages: Maximum number of pages to extract (default: 5 for faster processing)
        max_chars: Maximum characters to return (default: 8000 for reduced API load)

    Returns:
        Extracted text from the PDF
    """
    try:
        # Try docling-parse first for better structure-aware extraction
        parser = DoclingPdfParser()
        pdf_doc = parser.load(path_or_stream=str(pdf_path))

        text_parts = []
        total_chars = 0

        for page_no, pred_page in pdf_doc.iterate_pages():
            if page_no >= max_pages:
                break

            # Extract text at line level for better structure preservation
            page_lines = []
            for line in pred_page.iterate_cells(unit_type=TextCellUnit.LINE):
                page_lines.append(line.text)

            page_text = "\n".join(page_lines)

            # Add page text until we hit the character limit
            remaining_chars = max_chars - total_chars
            if remaining_chars <= 0:
                break

            text_parts.append(page_text[:remaining_chars])
            total_chars += len(page_text)

        extracted_text = "\n".join(text_parts).strip()

        # If we got very little text, the PDF might be scanned - try OCR
        if len(extracted_text) < 200:
            return _extract_with_ocr(pdf_path, max_pages, max_chars)

        return extracted_text

    except Exception as e:
        # Print warning that docling-parse failed for this file
        print(f"Warning: docling-parse failed for '{pdf_path.name}', falling back to PyMuPDF", file=sys.stderr)

        # Fall back to PyMuPDF if docling-parse fails
        try:
            doc = pymupdf.open(pdf_path)
            text_parts = []
            total_chars = 0

            for page_num in range(min(max_pages, len(doc))):
                page = doc[page_num]
                page_text = page.get_text()

                # Add page text until we hit the character limit
                remaining_chars = max_chars - total_chars
                if remaining_chars <= 0:
                    break

                text_parts.append(page_text[:remaining_chars])
                total_chars += len(page_text)

            doc.close()
            extracted_text = "\n".join(text_parts).strip()

            # If we got very little text, try OCR
            if len(extracted_text) < 200:
                return _extract_with_ocr(pdf_path, max_pages, max_chars)

            return extracted_text
        except Exception as fallback_error:
            print(f"Error: Both docling-parse and PyMuPDF failed for '{pdf_path.name}'", file=sys.stderr)
            raise RuntimeError(f"Failed to extract text from {pdf_path}: {e}, fallback also failed: {fallback_error}")


def _extract_with_ocr(pdf_path: Path, max_pages: int = 5, max_chars: int = 8000) -> str:
    """
    Extract text using OCR for scanned PDFs.

    Args:
        pdf_path: Path to the PDF file
        max_pages: Maximum number of pages to extract (default: 5)
        max_chars: Maximum characters to return (default: 8000)

    Returns:
        Extracted text from OCR
    """
    print(f"Info: Attempting OCR for '{pdf_path.name}' (low text content detected)", file=sys.stderr)
    try:
        doc = pymupdf.open(pdf_path)
        text_parts = []
        total_chars = 0

        for page_num in range(min(max_pages, len(doc))):
            page = doc[page_num]

            # Try OCR with Tesseract (if available)
            try:
                # get_textpage() with OCR enabled
                tp = page.get_textpage(flags=0)
                page_text = tp.extractText()

                # If still no text, try getting text from images
                if not page_text or len(page_text.strip()) < 50:
                    # Use get_text with 'text' option which includes OCR for images
                    page_text = page.get_text("text", flags=pymupdf.TEXT_PRESERVE_WHITESPACE)

            except Exception:
                # If OCR fails, get whatever text is available
                page_text = page.get_text()

            # Add page text until we hit the character limit
            remaining_chars = max_chars - total_chars
            if remaining_chars <= 0:
                break

            text_parts.append(page_text[:remaining_chars])
            total_chars += len(page_text)

        doc.close()
        return "\n".join(text_parts).strip()
    except Exception as e:
        print(f"Error: OCR extraction failed for '{pdf_path.name}'", file=sys.stderr)
        raise RuntimeError(f"OCR extraction failed for {pdf_path}: {e}")


def get_pdf_metadata(pdf_path: Path) -> dict:
    """
    Extract metadata from a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary with metadata (title, author, subject, etc.)
    """
    try:
        doc = pymupdf.open(pdf_path)
        metadata = doc.metadata
        doc.close()
        return metadata or {}
    except Exception as e:
        print(f"Warning: Failed to extract metadata from '{pdf_path.name}': {e}", file=sys.stderr)
        return {}


def extract_focused_metadata(pdf_path: Path) -> dict:
    """
    Extract focused metadata by analyzing the first few pages for common patterns.
    This helps supplement unreliable PDF metadata.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary with extracted metadata hints (title_hints, author_hints, year_hints)
    """
    try:
        doc = pymupdf.open(pdf_path)

        # Extract first 2 pages with more detail
        first_page_text = ""
        if len(doc) > 0:
            first_page_text = doc[0].get_text()

        # Look for year patterns (1900-2099)
        year_pattern = r'\b(19\d{2}|20\d{2})\b'
        years = re.findall(year_pattern, first_page_text)

        # Look for email addresses (often near author names)
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, first_page_text)

        # Extract first 500 chars (likely title and author area)
        header_text = first_page_text[:500]

        # Look for common author indicators
        author_indicators = ['by ', 'author:', 'authors:', 'written by']
        author_hints = []
        for indicator in author_indicators:
            if indicator in first_page_text.lower():
                idx = first_page_text.lower().index(indicator)
                # Extract ~100 chars after the indicator
                author_hints.append(first_page_text[idx:idx+100])

        doc.close()

        return {
            'header_text': header_text,
            'year_hints': years[:3] if years else [],  # First 3 years found
            'email_hints': emails[:3] if emails else [],  # First 3 emails found
            'author_hints': author_hints[:2] if author_hints else []  # First 2 author sections
        }
    except Exception as e:
        print(f"Warning: Failed to extract focused metadata from '{pdf_path.name}': {e}", file=sys.stderr)
        return {}
