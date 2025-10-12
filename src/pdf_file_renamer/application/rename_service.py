"""File rename service - handles the actual file operations."""

import shutil
from pathlib import Path

from pdf_file_renamer.domain.ports import FileRenamer


class RenameService(FileRenamer):
    """Service for renaming files with duplicate handling."""

    async def rename(self, original_path: Path, new_path: Path, dry_run: bool = True) -> bool:
        """
        Rename a file with duplicate handling.

        Args:
            original_path: Original file path
            new_path: New file path
            dry_run: If True, don't actually rename

        Returns:
            True if successful (or would be successful in dry-run)

        Raises:
            RuntimeError: If rename fails
        """
        try:
            # Check if source exists
            if not original_path.exists():
                msg = f"Source file does not exist: {original_path}"
                raise RuntimeError(msg)

            # Handle duplicates
            final_path = self._handle_duplicate(new_path)

            if dry_run:
                # In dry-run, just verify we could do the operation
                return True

            # Perform the rename
            if original_path.parent != final_path.parent:
                # Moving to different directory
                final_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(original_path), str(final_path))
            else:
                # Renaming in same directory
                original_path.rename(final_path)

            return True

        except Exception as e:
            msg = f"Failed to rename {original_path} to {new_path}: {e}"
            raise RuntimeError(msg) from e

    def _handle_duplicate(self, path: Path) -> Path:
        """
        Handle duplicate filenames by adding a counter suffix.

        Args:
            path: Desired path

        Returns:
            Path that doesn't conflict with existing files
        """
        if not path.exists():
            return path

        # Extract stem and suffix
        stem = path.stem
        suffix = path.suffix
        parent = path.parent

        # Try incrementing counter
        counter = 1
        while True:
            new_path = parent / f"{stem}-{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
