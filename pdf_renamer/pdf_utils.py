"""Utility functions for extracting text from PDF files."""

import pymupdf
from pathlib import Path


def extract_pdf_text(pdf_path: Path, max_pages: int = 3, max_chars: int = 3000) -> str:
    """
    Extract text from the first few pages of a PDF.

    Args:
        pdf_path: Path to the PDF file
        max_pages: Maximum number of pages to extract (default: 3)
        max_chars: Maximum characters to return (default: 3000)

    Returns:
        Extracted text from the PDF
    """
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
        return "\n".join(text_parts).strip()
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from {pdf_path}: {e}")


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
    except Exception:
        return {}
