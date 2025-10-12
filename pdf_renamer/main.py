"""Main script for renaming PDF files using LLM."""

import asyncio
import os
from pathlib import Path
from typing import Annotated
from collections import defaultdict
import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from dotenv import load_dotenv

from pdf_renamer.pdf_utils import extract_pdf_text, get_pdf_metadata, extract_focused_metadata
from pdf_renamer.filename_generator import FilenameGenerator

# Load environment variables from .env file
load_dotenv()

console = Console()

def cli():
    """CLI entry point."""
    typer.run(main)


async def prompt_interactive_rename(
    original_path: Path,
    suggested_name: str,
    confidence: str,
    reasoning: str,
    generator: FilenameGenerator,
    text_excerpt: str,
    metadata: dict,
) -> tuple[str, bool]:
    """
    Interactively prompt user for rename decision.

    Args:
        original_path: Original file path
        suggested_name: LLM-generated filename suggestion
        confidence: Confidence level
        reasoning: LLM reasoning
        generator: FilenameGenerator for retry
        text_excerpt: PDF text for retry
        metadata: PDF metadata for retry

    Returns:
        Tuple of (final_filename, should_rename)
        - If user skips: ("", False)
        - If user accepts/edits: (filename, True)
    """
    while True:
        # Create a compact panel with all info
        info_text = Text()
        info_text.append("Original:  ", style="bold cyan")
        info_text.append(f"{original_path.name}\n", style="cyan")
        info_text.append("Suggested: ", style="bold green")
        info_text.append(f"{suggested_name}.pdf\n", style="green")
        info_text.append("Confidence: ", style="bold yellow")
        info_text.append(f"{confidence}\n", style="yellow")
        info_text.append("Reasoning: ", style="bold white")
        info_text.append(reasoning, style="dim white")

        panel = Panel(
            info_text,
            title="[bold magenta]Rename Suggestion[/bold magenta]",
            border_style="magenta",
            padding=(1, 2)
        )

        console.print("\n")
        console.print(panel)

        # Show button-style options
        console.print("\n[bold]Actions:[/bold]")
        console.print("  [green on default][[/green on default][green bold on default] Y [/green bold on default][green on default]][/green on default] Accept  [yellow on default][[/yellow on default][yellow bold on default] E [/yellow bold on default][yellow on default]][/yellow on default] Edit  [blue on default][[/blue on default][blue bold on default] R [/blue bold on default][blue on default]][/blue on default] Retry  [red on default][[/red on default][red bold on default] N [/red bold on default][red on default]][/red on default] Skip")

        choice = Prompt.ask(
            "\nChoice",
            default="y",
            show_default=False
        ).lower().strip()

        if choice in ["y", "yes", ""]:
            # Accept suggestion
            return (suggested_name, True)

        elif choice in ["e", "edit"]:
            # Manual edit
            manual_name = Prompt.ask(
                "[yellow]Enter filename (without .pdf)[/yellow]",
                default=suggested_name
            ).strip()

            if manual_name:
                # Sanitize the manually entered filename
                clean_name = generator.sanitize_filename(manual_name)
                console.print(f"[green]✓ Using:[/green] {clean_name}.pdf")
                return (clean_name, True)
            else:
                console.print("[red]Empty filename, try again[/red]")
                continue

        elif choice in ["r", "retry"]:
            # Retry with LLM
            console.print("\n[blue]⟳ Generating new suggestion...[/blue]")
            try:
                new_suggestion = await generator.generate_filename(
                    original_filename=original_path.name,
                    text_excerpt=text_excerpt,
                    metadata=metadata
                )
                suggested_name = generator.sanitize_filename(new_suggestion.filename)
                confidence = new_suggestion.confidence
                reasoning = new_suggestion.reasoning
                # Continue loop to show new suggestion
                continue
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                console.print("[yellow]Choose another option[/yellow]")
                continue

        elif choice in ["n", "no", "skip"]:
            # Skip
            console.print("[yellow]⊘ Skipped[/yellow]")
            return ("", False)

        else:
            console.print(f"[red]Invalid: {choice}[/red]")
            continue

app = typer.Typer()


async def process_pdf(
    pdf_path: Path,
    generator: FilenameGenerator,
    semaphore: asyncio.Semaphore,
    status_tracker: dict,
    dry_run: bool = True
) -> tuple[Path, str, str, str, str, dict]:
    """
    Process a single PDF and generate a filename suggestion.

    Args:
        pdf_path: Path to the PDF file
        generator: FilenameGenerator instance
        semaphore: Semaphore to limit concurrent API calls
        status_tracker: Dictionary to track file status
        dry_run: If True, don't actually rename files

    Returns:
        Tuple of (original_path, suggested_name, confidence, reasoning, text_excerpt, metadata)
    """
    filename = pdf_path.name
    try:
        # Update status to extracting
        status_tracker[filename] = {"status": "Extracting", "stage": "📄"}

        # Parallelize PDF extraction operations using thread pool
        # This prevents blocking the async event loop
        text_task = asyncio.to_thread(extract_pdf_text, pdf_path)
        metadata_task = asyncio.to_thread(get_pdf_metadata, pdf_path)
        focused_metadata_task = asyncio.to_thread(extract_focused_metadata, pdf_path)

        # Wait for all extraction tasks to complete in parallel
        text, metadata, focused_metadata = await asyncio.gather(
            text_task,
            metadata_task,
            focused_metadata_task
        )

        # Combine metadata with focused extraction hints
        enhanced_metadata = {**metadata, 'focused': focused_metadata}

        # Use semaphore to limit concurrent API calls
        async with semaphore:
            # Update status to analyzing
            status_tracker[filename] = {"status": "Analyzing", "stage": "🤖"}

            # Generate filename suggestion
            suggestion = await generator.generate_filename(
                original_filename=pdf_path.name,
                text_excerpt=text,
                metadata=enhanced_metadata
            )

        # Sanitize the filename
        clean_filename = generator.sanitize_filename(suggestion.filename)

        # Mark as complete
        status_tracker[filename] = {"status": "Complete", "stage": "✓", "confidence": suggestion.confidence}

        return (
            pdf_path,
            clean_filename,
            suggestion.confidence,
            suggestion.reasoning,
            text,
            enhanced_metadata
        )
    except Exception as e:
        status_tracker[filename] = {"status": "Error", "stage": "✗", "error": str(e)}
        return (pdf_path, "", "error", str(e), "", {})


@app.command()
def main(
    directory: Annotated[
        Path,
        typer.Argument(help="Directory containing PDF files to rename")
    ] = Path.cwd(),
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run/--no-dry-run", help="Show suggestions without renaming")
    ] = True,
    model: Annotated[
        str,
        typer.Option("--model", help="Model to use (works with any OpenAI-compatible API)")
    ] = "llama3.2",
    url: Annotated[
        str | None,
        typer.Option("--url", help="Custom base URL for OpenAI-compatible APIs")
    ] = "http://localhost:11434/v1",
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Confirm each rename")
    ] = False,
    pattern: Annotated[
        str,
        typer.Option("--pattern", help="Glob pattern for PDF files")
    ] = "*.pdf",
    max_concurrent_api: Annotated[
        int,
        typer.Option("--max-concurrent-api", help="Maximum concurrent API calls (default: 3)")
    ] = 3,
    max_concurrent_pdf: Annotated[
        int,
        typer.Option("--max-concurrent-pdf", help="Maximum concurrent PDF extractions (default: 10)")
    ] = 10,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Move renamed files to this directory")
    ] = None,
):
    """
    Rename PDF files in a directory using LLM-generated suggestions.
    """
    # Validate output directory
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        if not output_dir.is_dir():
            console.print(f"[red]Error: {output_dir} is not a directory[/red]")
            raise typer.Exit(1)

    # Use Ollama by default, or custom URL from env/CLI
    base_url = url or os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")

    # API key is optional for local Ollama, but required for OpenAI
    api_key = os.getenv("OPENAI_API_KEY")

    # Find PDF files
    pdf_files = sorted(directory.glob(pattern))
    if not pdf_files:
        console.print(f"[yellow]No PDF files found matching '{pattern}' in {directory}[/yellow]")
        raise typer.Exit(0)

    console.print(f"Found {len(pdf_files)} PDF files to process\n")

    # Initialize generator
    generator = FilenameGenerator(model_name=model, api_key=api_key, base_url=base_url)

    # Process files with controlled concurrency and live progress display
    async def process_all():
        # Semaphore to limit concurrent API calls (prevents overwhelming the API)
        api_semaphore = asyncio.Semaphore(max_concurrent_api)

        # Semaphore to limit concurrent PDF extractions (prevents high memory usage)
        pdf_semaphore = asyncio.Semaphore(max_concurrent_pdf)

        # Status tracker for all files
        status_tracker = {}

        def create_display():
            """Create the live display layout."""
            # Create a table showing currently active files
            table = Table(title="Processing Status", expand=True, show_header=True, header_style="bold magenta")
            table.add_column("File", style="cyan", no_wrap=False, width=40)
            table.add_column("Stage", justify="center", width=8)
            table.add_column("Status", style="yellow", width=12)
            table.add_column("Details", style="dim", no_wrap=False)

            # Count statuses
            total = len(pdf_files)
            completed = sum(1 for s in status_tracker.values() if s.get("status") == "Complete")
            extracting = sum(1 for s in status_tracker.values() if s.get("status") == "Extracting")
            analyzing = sum(1 for s in status_tracker.values() if s.get("status") == "Analyzing")
            errors = sum(1 for s in status_tracker.values() if s.get("status") == "Error")
            pending = total - completed - extracting - analyzing - errors

            # Show only active and recent files (last 10 completed + all active)
            active_files = []
            completed_files = []

            for filename, info in status_tracker.items():
                if info.get("status") in ["Extracting", "Analyzing"]:
                    active_files.append((filename, info))
                elif info.get("status") in ["Complete", "Error"]:
                    completed_files.append((filename, info))

            # Show active files first
            for filename, info in active_files:
                stage = info.get("stage", "")
                status = info.get("status", "")
                details = ""
                if info.get("confidence"):
                    details = f"Confidence: {info['confidence']}"

                # Truncate filename for display
                display_name = filename if len(filename) <= 40 else filename[:37] + "..."
                table.add_row(display_name, stage, status, details)

            # Show last 5 completed files
            for filename, info in completed_files[-5:]:
                stage = info.get("stage", "")
                status = info.get("status", "")
                details = ""
                if info.get("confidence"):
                    details = f"Confidence: {info['confidence']}"
                elif info.get("error"):
                    details = info["error"][:50]

                # Truncate filename for display
                display_name = filename if len(filename) <= 40 else filename[:37] + "..."
                style = "green" if status == "Complete" else "red" if status == "Error" else "white"
                table.add_row(f"[{style}]{display_name}[/{style}]", stage, status, details)

            # Create stats panel
            stats = Text()
            stats.append("Total: ", style="bold")
            stats.append(f"{total}", style="white")
            stats.append(" | ", style="dim")
            stats.append("Pending: ", style="bold")
            stats.append(f"{pending}", style="cyan")
            stats.append(" | ", style="dim")
            stats.append("Extracting: ", style="bold")
            stats.append(f"{extracting}", style="blue")
            stats.append(" | ", style="dim")
            stats.append("Analyzing: ", style="bold")
            stats.append(f"{analyzing}", style="yellow")
            stats.append(" | ", style="dim")
            stats.append("Complete: ", style="bold green")
            stats.append(f"{completed}", style="green")

            if errors > 0:
                stats.append(" | ", style="dim")
                stats.append("Errors: ", style="bold red")
                stats.append(f"{errors}", style="red")

            # Progress bar
            progress_pct = (completed / total * 100) if total > 0 else 0
            progress_bar = f"[{'█' * int(progress_pct / 2)}{' ' * (50 - int(progress_pct / 2))}] {progress_pct:.1f}%"

            layout = Layout()
            layout.split_column(
                Layout(Panel(stats, title="📊 Progress", border_style="blue"), size=3),
                Layout(Panel(Text(progress_bar, style="green bold"), border_style="green"), size=3),
                Layout(table)
            )

            return layout

        async def process_with_limits(pdf: Path) -> tuple[Path, str, str, str]:
            """Process a single PDF with semaphore limits."""
            async with pdf_semaphore:
                return await process_pdf(
                    pdf,
                    generator,
                    api_semaphore,
                    status_tracker,
                    dry_run
                )

        # Create tasks for all files
        tasks = [process_with_limits(pdf) for pdf in pdf_files]

        # Run with live display
        with Live(create_display(), console=console, refresh_per_second=4) as live:
            async def update_display():
                """Periodically update the display."""
                while True:
                    live.update(create_display())
                    await asyncio.sleep(0.25)

            # Start display updater
            display_task = asyncio.create_task(update_display())

            # Process all files
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Cancel display updater
            display_task.cancel()
            try:
                await display_task
            except asyncio.CancelledError:
                pass

            # Final update
            live.update(create_display())

            return results

    console.print(f"[bold]Processing {len(pdf_files)} PDFs with max {max_concurrent_api} concurrent API calls and {max_concurrent_pdf} concurrent extractions[/bold]\n")
    results = asyncio.run(process_all())

    # Display results (only if not interactive mode)
    if not interactive:
        table = Table(title="Rename Suggestions")
        table.add_column("Original", style="cyan", no_wrap=False)
        table.add_column("Suggested", style="green", no_wrap=False)
        table.add_column("Confidence", style="yellow")
        table.add_column("Reasoning", style="white", no_wrap=False)

        for result in results:
            # Handle exceptions from gather(return_exceptions=True)
            if isinstance(result, Exception):
                console.print(f"[red]Unexpected error: {result}[/red]")
                continue

            original_path, suggested_name, confidence, reasoning, _, _ = result
            if suggested_name:
                table.add_row(
                    original_path.name,
                    f"{suggested_name}.pdf",
                    confidence,
                    reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
                )

        console.print(table)

    # Perform renames if not dry run (or interactive mode)
    if not dry_run or interactive:
        if not interactive:
            console.print("\n[bold yellow]Performing renames...[/bold yellow]")

        renamed_count = 0
        skipped_count = 0

        async def process_renames():
            """Process renames, potentially with interactive prompts."""
            nonlocal renamed_count, skipped_count

            for result in results:
                # Skip exceptions
                if isinstance(result, Exception):
                    skipped_count += 1
                    continue

                original_path, suggested_name, confidence, reasoning, text_excerpt, metadata = result
                if not suggested_name or confidence == "error":
                    skipped_count += 1
                    continue

                # Interactive mode: prompt user for decision
                if interactive:
                    final_name, should_rename = await prompt_interactive_rename(
                        original_path=original_path,
                        suggested_name=suggested_name,
                        confidence=confidence,
                        reasoning=reasoning,
                        generator=generator,
                        text_excerpt=text_excerpt,
                        metadata=metadata,
                    )

                    if not should_rename:
                        skipped_count += 1
                        continue

                    # Use the user's choice (could be original suggestion, edited, or retry result)
                    suggested_name = final_name

                # Determine target path (output directory or same directory)
                if output_dir:
                    new_path = output_dir / f"{suggested_name}.pdf"
                else:
                    new_path = original_path.parent / f"{suggested_name}.pdf"

                # Skip if filename is the same and no output directory
                if not output_dir and original_path.name == new_path.name:
                    skipped_count += 1
                    continue

                # Handle duplicates by adding a counter suffix
                final_path = new_path
                if final_path.exists():
                    counter = 1
                    while final_path.exists():
                        if output_dir:
                            final_path = output_dir / f"{suggested_name}-{counter}.pdf"
                        else:
                            final_path = original_path.parent / f"{suggested_name}-{counter}.pdf"
                        counter += 1
                    console.print(f"[yellow]Duplicate detected, using: {final_path.name}[/yellow]")

                # Only perform rename if not in dry_run mode
                if not dry_run:
                    try:
                        if output_dir:
                            # Move to output directory with new name
                            import shutil
                            shutil.move(str(original_path), str(final_path))
                            console.print(f"[green]✓[/green] {original_path.name} → {final_path}")
                        else:
                            # Rename in place
                            original_path.rename(final_path)
                            console.print(f"[green]✓[/green] {original_path.name} → {final_path.name}")
                        renamed_count += 1
                    except Exception as e:
                        console.print(f"[red]✗[/red] Failed to process {original_path.name}: {e}")
                        skipped_count += 1
                else:
                    # In dry run with interactive, show what would happen
                    console.print(f"[dim]Would rename: {original_path.name} → {final_path.name}[/dim]")
                    renamed_count += 1

        asyncio.run(process_renames())

        console.print(f"\n[bold]Summary:[/bold] {renamed_count} renamed, {skipped_count} skipped")
    else:
        console.print("\n[bold yellow]Dry run mode - no files were renamed[/bold yellow]")
        console.print("Run without --dry-run to apply changes")


if __name__ == "__main__":
    app()
