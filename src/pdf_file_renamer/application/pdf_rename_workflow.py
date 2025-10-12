"""PDF rename workflow - orchestrates the complete process."""

import asyncio
from collections.abc import Callable
from pathlib import Path

from pdf_file_renamer.domain.models import FileRenameOperation
from pdf_file_renamer.domain.ports import (
    FilenameGenerator,
    FileRenamer,
    PDFExtractor,
)


class PDFRenameWorkflow:
    """
    Orchestrates the PDF rename workflow.

    This class follows the Single Responsibility Principle - it only coordinates
    the workflow, delegating actual work to specialized services.
    """

    def __init__(
        self,
        pdf_extractor: PDFExtractor,
        filename_generator: FilenameGenerator,
        file_renamer: FileRenamer,
        max_concurrent_api: int = 3,
        max_concurrent_pdf: int = 10,
    ) -> None:
        """
        Initialize the workflow.

        Args:
            pdf_extractor: PDF extraction service
            filename_generator: Filename generation service
            file_renamer: File renaming service
            max_concurrent_api: Maximum concurrent API calls
            max_concurrent_pdf: Maximum concurrent PDF extractions
        """
        self.pdf_extractor = pdf_extractor
        self.filename_generator = filename_generator
        self.file_renamer = file_renamer
        self.api_semaphore = asyncio.Semaphore(max_concurrent_api)
        self.pdf_semaphore = asyncio.Semaphore(max_concurrent_pdf)

    async def process_pdf(
        self,
        pdf_path: Path,
        status_callback: Callable[[str, dict[str, str]], None] | None = None,
    ) -> FileRenameOperation | None:
        """
        Process a single PDF file.

        Args:
            pdf_path: Path to PDF file
            status_callback: Optional callback for status updates (filename, status_dict)

        Returns:
            FileRenameOperation if successful, None if error
        """
        filename = pdf_path.name

        try:
            # Update status: extracting
            if status_callback:
                status_callback(filename, {"status": "Extracting", "stage": "📄"})

            # Extract PDF content (with PDF semaphore to limit memory usage)
            async with self.pdf_semaphore:
                content = await self.pdf_extractor.extract(pdf_path)

            # Generate filename (with API semaphore to limit API load)
            if status_callback:
                status_callback(filename, {"status": "Analyzing", "stage": "🤖"})

            async with self.api_semaphore:
                result = await self.filename_generator.generate(filename, content)

            # Mark complete
            if status_callback:
                status_callback(
                    filename,
                    {
                        "status": "Complete",
                        "stage": "✓",
                        "confidence": result.confidence.value,
                    },
                )

            return FileRenameOperation(
                original_path=pdf_path,
                suggested_filename=result.filename,
                confidence=result.confidence,
                reasoning=result.reasoning,
                text_excerpt=content.text,
                metadata=content.metadata,
            )

        except Exception as e:
            if status_callback:
                status_callback(filename, {"status": "Error", "stage": "✗", "error": str(e)})
            return None

    async def process_batch(
        self,
        pdf_paths: list[Path],
        status_callback: Callable[[str, dict[str, str]], None] | None = None,
    ) -> list[FileRenameOperation | None]:
        """
        Process multiple PDF files concurrently.

        Args:
            pdf_paths: List of PDF paths to process
            status_callback: Optional callback for status updates

        Returns:
            List of FileRenameOperation results (None for failures)
        """
        tasks = [self.process_pdf(pdf, status_callback) for pdf in pdf_paths]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def execute_rename(
        self,
        operation: FileRenameOperation,
        output_dir: Path | None = None,
        dry_run: bool = True,
    ) -> bool:
        """
        Execute a rename operation.

        Args:
            operation: The rename operation to execute
            output_dir: Optional output directory
            dry_run: If True, don't actually rename

        Returns:
            True if successful

        Raises:
            RuntimeError: If rename fails
        """
        new_path = operation.create_new_path(output_dir)
        return await self.file_renamer.rename(operation.original_path, new_path, dry_run)
