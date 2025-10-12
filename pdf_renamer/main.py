"""Main script for renaming PDF files using LLM."""

import asyncio
import os
from pathlib import Path
from typing import Annotated
import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from dotenv import load_dotenv

from pdf_renamer.pdf_utils import extract_pdf_text, get_pdf_metadata
from pdf_renamer.filename_generator import FilenameGenerator

# Load environment variables from .env file
load_dotenv()

app = typer.Typer(help="Rename PDF files intelligently using LLM")
console = Console()


async def process_pdf(
    pdf_path: Path,
    generator: FilenameGenerator,
    dry_run: bool = True
) -> tuple[Path, str, str, str]:
    """
    Process a single PDF and generate a filename suggestion.

    Args:
        pdf_path: Path to the PDF file
        generator: FilenameGenerator instance
        dry_run: If True, don't actually rename files

    Returns:
        Tuple of (original_path, suggested_name, confidence, reasoning)
    """
    try:
        # Extract text and metadata
        text = extract_pdf_text(pdf_path)
        metadata = get_pdf_metadata(pdf_path)

        # Generate filename suggestion
        suggestion = await generator.generate_filename(
            original_filename=pdf_path.name,
            text_excerpt=text,
            metadata=metadata
        )

        # Sanitize the filename
        clean_filename = generator.sanitize_filename(suggestion.filename)

        return (
            pdf_path,
            clean_filename,
            suggestion.confidence,
            suggestion.reasoning
        )
    except Exception as e:
        console.print(f"[red]Error processing {pdf_path.name}: {e}[/red]")
        return (pdf_path, "", "error", str(e))


@app.callback(invoke_without_command=True)
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
):
    """
    Rename PDF files in a directory using LLM-generated suggestions.
    """
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

    # Process files
    async def process_all():
        tasks = [process_pdf(pdf, generator, dry_run) for pdf in pdf_files]
        return await asyncio.gather(*tasks)

    results = asyncio.run(process_all())

    # Display results
    table = Table(title="Rename Suggestions")
    table.add_column("Original", style="cyan", no_wrap=False)
    table.add_column("Suggested", style="green", no_wrap=False)
    table.add_column("Confidence", style="yellow")
    table.add_column("Reasoning", style="white", no_wrap=False)

    for original_path, suggested_name, confidence, reasoning in results:
        if suggested_name:
            table.add_row(
                original_path.name,
                f"{suggested_name}.pdf",
                confidence,
                reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
            )

    console.print(table)

    # Perform renames if not dry run
    if not dry_run:
        console.print("\n[bold yellow]Performing renames...[/bold yellow]")

        renamed_count = 0
        skipped_count = 0

        for original_path, suggested_name, confidence, _ in results:
            if not suggested_name or confidence == "error":
                skipped_count += 1
                continue

            new_path = original_path.parent / f"{suggested_name}.pdf"

            # Skip if filename is the same
            if original_path.name == new_path.name:
                skipped_count += 1
                continue

            # Check if target file already exists
            if new_path.exists():
                console.print(f"[yellow]Skipping {original_path.name}: target already exists[/yellow]")
                skipped_count += 1
                continue

            # Interactive confirmation
            if interactive:
                if not Confirm.ask(f"Rename {original_path.name} → {new_path.name}?"):
                    skipped_count += 1
                    continue

            try:
                original_path.rename(new_path)
                console.print(f"[green]✓[/green] {original_path.name} → {new_path.name}")
                renamed_count += 1
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to rename {original_path.name}: {e}")
                skipped_count += 1

        console.print(f"\n[bold]Summary:[/bold] {renamed_count} renamed, {skipped_count} skipped")
    else:
        console.print("\n[bold yellow]Dry run mode - no files were renamed[/bold yellow]")
        console.print("Run without --dry-run to apply changes")


if __name__ == "__main__":
    app()
