"""CLI interface using Typer."""

import asyncio
import contextlib
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.live import Live

from pdf_file_renamer.application import (
    FilenameService,
    PDFRenameWorkflow,
    RenameService,
)
from pdf_file_renamer.infrastructure.config import Settings
from pdf_file_renamer.infrastructure.doi import PDF2DOIExtractor
from pdf_file_renamer.infrastructure.llm import PydanticAIProvider
from pdf_file_renamer.infrastructure.pdf import (
    CompositePDFExtractor,
    DoclingPDFExtractor,
    PyMuPDFExtractor,
)
from pdf_file_renamer.presentation.formatters import (
    InteractivePrompt,
    ProgressDisplay,
    ResultsTable,
)

app = typer.Typer(help="Intelligent PDF renaming using LLMs")
console = Console()


def create_workflow(settings: Settings) -> PDFRenameWorkflow:
    """
    Create the workflow with all dependencies (Dependency Injection).

    This is the "Composition Root" where we wire up all dependencies.

    Args:
        settings: Application settings

    Returns:
        Configured PDFRenameWorkflow
    """
    # Create PDF extractor (composite with fallback strategy)
    extractors = [
        DoclingPDFExtractor(max_pages=settings.pdf_max_pages, max_chars=settings.pdf_max_chars),
        PyMuPDFExtractor(
            max_pages=settings.pdf_max_pages,
            max_chars=settings.pdf_max_chars,
            enable_ocr=True,
        ),
    ]
    pdf_extractor = CompositePDFExtractor(extractors)

    # Create LLM provider
    llm_provider = PydanticAIProvider(
        model_name=settings.llm_model,
        api_key=settings.openai_api_key,
        base_url=settings.llm_base_url,
        retry_max_attempts=settings.retry_max_attempts,
        retry_min_wait=settings.retry_min_wait,
        retry_max_wait=settings.retry_max_wait,
    )

    # Create DOI extractor
    doi_extractor = PDF2DOIExtractor()

    # Create application services
    filename_service = FilenameService(llm_provider)
    file_renamer = RenameService()

    # Create workflow
    return PDFRenameWorkflow(
        pdf_extractor=pdf_extractor,
        filename_generator=filename_service,
        file_renamer=file_renamer,
        doi_extractor=doi_extractor,
        max_concurrent_api=settings.max_concurrent_api,
        max_concurrent_pdf=settings.max_concurrent_pdf,
    )


@app.command()
def main(
    directory: Annotated[
        Path, typer.Argument(help="Directory containing PDF files to rename")
    ] = Path.cwd(),
    dry_run: Annotated[
        bool, typer.Option("--dry-run/--no-dry-run", help="Show suggestions without renaming")
    ] = True,
    model: Annotated[
        str | None,
        typer.Option("--model", help="Model to use (overrides config)"),
    ] = None,
    url: Annotated[
        str | None,
        typer.Option("--url", help="Custom base URL for OpenAI-compatible APIs"),
    ] = None,
    interactive: Annotated[
        bool, typer.Option("--interactive", "-i", help="Confirm each rename")
    ] = False,
    pattern: Annotated[str, typer.Option("--pattern", help="Glob pattern for PDF files")] = "*.pdf",
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Move renamed files to this directory"),
    ] = None,
) -> None:
    """Rename PDF files in a directory using LLM-generated suggestions."""
    # Load settings
    settings = Settings()

    # Override settings from CLI args
    if model:
        settings.llm_model = model
    if url:
        settings.llm_base_url = url

    # Validate output directory
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        if not output_dir.is_dir():
            console.print(f"[red]Error: {output_dir} is not a directory[/red]")
            raise typer.Exit(1)

    # Find PDF files
    pdf_files = sorted(directory.glob(pattern))
    if not pdf_files:
        console.print(f"[yellow]No PDF files found matching '{pattern}' in {directory}[/yellow]")
        raise typer.Exit(0)

    console.print(f"Found {len(pdf_files)} PDF files to process\n")

    # Create workflow
    workflow = create_workflow(settings)

    # Process files with progress display
    async def process_all() -> list:
        progress = ProgressDisplay(console, len(pdf_files))

        def status_callback(filename: str, status: dict[str, str]) -> None:
            progress.update_status(filename, status)

        # Run with live display
        with Live(progress.create_display(), console=console, refresh_per_second=4) as live:

            async def update_display() -> None:
                while True:
                    live.update(progress.create_display())
                    await asyncio.sleep(0.25)

            display_task = asyncio.create_task(update_display())

            results = await workflow.process_batch(pdf_files, status_callback)

            display_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await display_task

            live.update(progress.create_display())

        return results

    # Run processing
    console.print(
        f"[bold]Processing {len(pdf_files)} PDFs with max {settings.max_concurrent_api} "
        f"concurrent API calls and {settings.max_concurrent_pdf} concurrent extractions[/bold]\n"
    )
    results = asyncio.run(process_all())

    # Filter successful operations
    operations = [r for r in results if r is not None]

    if not operations:
        console.print("[red]No files could be processed successfully[/red]")
        raise typer.Exit(1)

    # Display results (if not interactive)
    if not interactive:
        ResultsTable.create(operations, console)

    # Execute renames
    if not dry_run or interactive:
        renamed_count = 0
        skipped_count = 0

        async def execute_renames() -> None:
            nonlocal renamed_count, skipped_count

            prompt = InteractivePrompt(console) if interactive else None

            for operation in operations:
                # Interactive mode
                if interactive and prompt:
                    final_name, should_rename = await prompt.prompt_for_action(operation)
                    if not should_rename:
                        skipped_count += 1
                        continue
                    # Update operation with user's choice
                    operation.suggested_filename = final_name

                # Skip if no change
                if not output_dir and operation.original_path.name == operation.new_filename:
                    skipped_count += 1
                    continue

                # Execute rename
                try:
                    success = await workflow.execute_rename(operation, output_dir, dry_run)
                    if success:
                        if dry_run:
                            console.print(
                                f"[dim]Would rename: {operation.original_path.name} → "
                                f"{operation.new_filename}[/dim]"
                            )
                        else:
                            new_path = operation.create_new_path(output_dir)
                            console.print(
                                f"[green]✓[/green] {operation.original_path.name} → {new_path.name}"
                            )
                        renamed_count += 1
                except Exception as e:
                    console.print(
                        f"[red]✗[/red] Failed to rename {operation.original_path.name}: {e}"
                    )
                    skipped_count += 1

        asyncio.run(execute_renames())
        console.print(f"\n[bold]Summary:[/bold] {renamed_count} renamed, {skipped_count} skipped")
    else:
        console.print("\n[bold yellow]Dry run mode - no files were renamed[/bold yellow]")
        console.print("Run without --dry-run to apply changes")


if __name__ == "__main__":
    app()
