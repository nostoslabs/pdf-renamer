"""Display formatters and UI components."""

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from pdf_file_renamer.domain.models import ConfidenceLevel, FileRenameOperation


class ProgressDisplay:
    """Handles progress display for batch processing."""

    def __init__(self, console: Console, total_files: int) -> None:
        """
        Initialize the progress display.

        Args:
            console: Rich console for output
            total_files: Total number of files to process
        """
        self.console = console
        self.total_files = total_files
        self.status_tracker: dict[str, dict[str, str]] = {}

    def update_status(self, filename: str, status: dict[str, str]) -> None:
        """Update status for a file."""
        self.status_tracker[filename] = status

    def create_display(self) -> Layout:
        """Create the live display layout."""
        # Create table
        table = Table(
            title="Processing Status",
            expand=True,
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("File", style="cyan", no_wrap=False, width=40)
        table.add_column("Stage", justify="center", width=8)
        table.add_column("Status", style="yellow", width=12)
        table.add_column("Details", style="dim", no_wrap=False)

        # Count statuses
        completed = sum(1 for s in self.status_tracker.values() if s.get("status") == "Complete")
        extracting = sum(1 for s in self.status_tracker.values() if s.get("status") == "Extracting")
        analyzing = sum(1 for s in self.status_tracker.values() if s.get("status") == "Analyzing")
        errors = sum(1 for s in self.status_tracker.values() if s.get("status") == "Error")
        pending = self.total_files - completed - extracting - analyzing - errors

        # Separate files by status
        active_files = []
        completed_files = []

        for filename, info in self.status_tracker.items():
            if info.get("status") in ["Extracting", "Analyzing"]:
                active_files.append((filename, info))
            elif info.get("status") in ["Complete", "Error"]:
                completed_files.append((filename, info))

        # Show active files
        for filename, info in active_files:
            display_name = filename if len(filename) <= 40 else filename[:37] + "..."
            table.add_row(
                display_name,
                info.get("stage", ""),
                info.get("status", ""),
                info.get("confidence", ""),
            )

        # Show last 5 completed files
        for filename, info in completed_files[-5:]:
            display_name = filename if len(filename) <= 40 else filename[:37] + "..."
            status = info.get("status", "")
            style = "green" if status == "Complete" else "red"
            details = info.get("confidence", "") or info.get("error", "")[:50]
            table.add_row(
                f"[{style}]{display_name}[/{style}]",
                info.get("stage", ""),
                status,
                details,
            )

        # Stats panel
        stats = Text()
        stats.append("Total: ", style="bold")
        stats.append(f"{self.total_files}", style="white")
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
        progress_pct = (completed / self.total_files * 100) if self.total_files > 0 else 0
        filled = int(progress_pct / 2)
        progress_bar = f"[{'█' * filled}{' ' * (50 - filled)}] {progress_pct:.1f}%"

        # Layout
        layout = Layout()
        layout.split_column(
            Layout(Panel(stats, title="📊 Progress", border_style="blue"), size=3),
            Layout(Panel(Text(progress_bar, style="green bold"), border_style="green"), size=3),
            Layout(table),
        )

        return layout


class InteractivePrompt:
    """Handles interactive prompts for rename confirmation."""

    def __init__(self, console: Console) -> None:
        """Initialize the interactive prompt."""
        self.console = console

    async def prompt_for_action(self, operation: FileRenameOperation) -> tuple[str, bool]:
        """
        Prompt user for action on a rename operation.

        Args:
            operation: The rename operation

        Returns:
            Tuple of (final_filename, should_rename)
        """
        while True:
            # Display info panel
            info_text = Text()
            info_text.append("Original:  ", style="bold cyan")
            info_text.append(f"{operation.original_path.name}\n", style="cyan")
            info_text.append("Suggested: ", style="bold green")
            info_text.append(f"{operation.new_filename}\n", style="green")
            info_text.append("Confidence: ", style="bold yellow")
            # Handle both enum and string confidence
            conf_str = (
                operation.confidence.value
                if isinstance(operation.confidence, ConfidenceLevel)
                else operation.confidence
            )
            info_text.append(f"{conf_str}\n", style="yellow")
            info_text.append("Reasoning: ", style="bold white")
            info_text.append(operation.reasoning, style="dim white")

            panel = Panel(
                info_text,
                title="[bold magenta]Rename Suggestion[/bold magenta]",
                border_style="magenta",
                padding=(1, 2),
            )

            self.console.print("\n")
            self.console.print(panel)

            # Show options
            self.console.print("\n[bold]Actions:[/bold]")
            self.console.print(
                "  [green on default][[/green on default][green bold on default] Y [/green bold on default][green on default]][/green on default] Accept  "
                "[yellow on default][[/yellow on default][yellow bold on default] E [/yellow bold on default][yellow on default]][/yellow on default] Edit  "
                "[red on default][[/red on default][red bold on default] N [/red bold on default][red on default]][/red on default] Skip"
            )

            choice = Prompt.ask("\nChoice", default="y", show_default=False).lower().strip()

            if choice in ["y", "yes", ""]:
                return (operation.suggested_filename, True)
            elif choice in ["e", "edit"]:
                manual_name = Prompt.ask(
                    "[yellow]Enter filename (without .pdf)[/yellow]",
                    default=operation.suggested_filename,
                ).strip()
                if manual_name:
                    return (manual_name, True)
                else:
                    self.console.print("[red]Empty filename, try again[/red]")
                    continue
            elif choice in ["n", "no", "skip"]:
                self.console.print("[yellow]⊘ Skipped[/yellow]")
                return ("", False)
            else:
                self.console.print(f"[red]Invalid: {choice}[/red]")
                continue


class ResultsTable:
    """Formats results as a table."""

    @staticmethod
    def create(operations: list[FileRenameOperation], console: Console) -> None:
        """Create and print a results table."""
        table = Table(title="Rename Suggestions")
        table.add_column("Original", style="cyan", no_wrap=False)
        table.add_column("Suggested", style="green", no_wrap=False)
        table.add_column("Confidence", style="yellow")
        table.add_column("Reasoning", style="white", no_wrap=False)

        for op in operations:
            reasoning = op.reasoning
            if len(reasoning) > 100:
                reasoning = reasoning[:100] + "..."
            # Handle both enum and string confidence
            conf_str = (
                op.confidence.value if isinstance(op.confidence, ConfidenceLevel) else op.confidence
            )
            table.add_row(
                op.original_path.name,
                op.new_filename,
                conf_str,
                reasoning,
            )

        console.print(table)
