"""Tests for rename service."""

from pathlib import Path

import pytest

from pdf_file_renamer.application.rename_service import RenameService


class TestRenameService:
    """Tests for RenameService."""

    @pytest.mark.asyncio
    async def test_rename_dry_run(self, tmp_path: Path) -> None:
        """Test rename in dry-run mode."""
        service = RenameService()

        # Create a test file
        src = tmp_path / "test.pdf"
        src.write_text("test content")

        dst = tmp_path / "renamed.pdf"

        # Dry run should succeed without actually renaming
        result = await service.rename(src, dst, dry_run=True)
        assert result is True
        assert src.exists()
        assert not dst.exists()

    @pytest.mark.asyncio
    async def test_rename_actual(self, tmp_path: Path) -> None:
        """Test actual rename."""
        service = RenameService()

        src = tmp_path / "test.pdf"
        src.write_text("test content")
        dst = tmp_path / "renamed.pdf"

        result = await service.rename(src, dst, dry_run=False)
        assert result is True
        assert not src.exists()
        assert dst.exists()
        assert dst.read_text() == "test content"

    @pytest.mark.asyncio
    async def test_rename_with_duplicate(self, tmp_path: Path) -> None:
        """Test rename handles duplicates."""
        service = RenameService()

        # Create source and existing target
        src = tmp_path / "test.pdf"
        src.write_text("new content")

        existing = tmp_path / "renamed.pdf"
        existing.write_text("existing content")

        # Should create renamed-1.pdf
        result = await service.rename(src, existing, dry_run=False)
        assert result is True
        assert not src.exists()
        assert existing.exists()  # Original unchanged
        assert existing.read_text() == "existing content"

        # New file with counter
        renamed_with_counter = tmp_path / "renamed-1.pdf"
        assert renamed_with_counter.exists()
        assert renamed_with_counter.read_text() == "new content"

    @pytest.mark.asyncio
    async def test_rename_to_different_directory(self, tmp_path: Path) -> None:
        """Test rename to different directory."""
        service = RenameService()

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        src = src_dir / "test.pdf"
        src.write_text("test content")

        dst_dir = tmp_path / "dst"
        dst = dst_dir / "renamed.pdf"

        result = await service.rename(src, dst, dry_run=False)
        assert result is True
        assert not src.exists()
        assert dst.exists()
        assert dst.read_text() == "test content"

    @pytest.mark.asyncio
    async def test_rename_nonexistent_file(self, tmp_path: Path) -> None:
        """Test rename fails for nonexistent file."""
        service = RenameService()

        src = tmp_path / "nonexistent.pdf"
        dst = tmp_path / "renamed.pdf"

        with pytest.raises(RuntimeError, match="does not exist"):
            await service.rename(src, dst, dry_run=False)
