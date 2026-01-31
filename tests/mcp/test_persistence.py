"""Tests for atomic file write operations."""

import os
import signal
import tempfile
from pathlib import Path

import pytest

from specify_cli.mcp.session.persistence import atomic_write


def test_atomic_write_creates_file(tmp_path):
    """Test that atomic_write creates a file with correct content."""
    file_path = tmp_path / "test.txt"
    content = "Hello, World!"
    
    atomic_write(file_path, content)
    
    assert file_path.exists()
    assert file_path.read_text() == content


def test_atomic_write_overwrites_existing(tmp_path):
    """Test that atomic_write overwrites existing file."""
    file_path = tmp_path / "test.txt"
    
    # Write initial content
    file_path.write_text("Old content")
    
    # Overwrite with atomic write
    new_content = "New content"
    atomic_write(file_path, new_content)
    
    assert file_path.read_text() == new_content


def test_atomic_write_creates_parent_directory(tmp_path):
    """Test that atomic_write creates parent directories if needed."""
    file_path = tmp_path / "subdir" / "test.txt"
    content = "Test content"
    
    atomic_write(file_path, content)
    
    assert file_path.exists()
    assert file_path.read_text() == content


def test_atomic_write_uses_temp_file_in_same_directory(tmp_path):
    """Test that atomic_write creates temp file in same directory as target."""
    file_path = tmp_path / "test.txt"
    content = "Test content"
    
    # Track files created during write
    files_before = set(tmp_path.iterdir())
    
    atomic_write(file_path, content)
    
    files_after = set(tmp_path.iterdir())
    
    # Should only have the target file (temp file should be cleaned up)
    assert files_after == files_before | {file_path}


def test_atomic_write_handles_unicode(tmp_path):
    """Test that atomic_write handles unicode content correctly."""
    file_path = tmp_path / "unicode.txt"
    content = "Hello 世界 🌍 مرحبا"
    
    atomic_write(file_path, content)
    
    assert file_path.read_text(encoding="utf-8") == content


def test_atomic_write_error_cleanup(tmp_path):
    """Test that atomic_write cleans up temp file on error."""
    # Create a file path that will fail during write
    # (by making parent directory read-only after temp file creation)
    file_path = tmp_path / "test.txt"
    
    # Patch os.replace to simulate failure
    import unittest.mock as mock
    
    with mock.patch("os.replace", side_effect=OSError("Simulated error")):
        with pytest.raises(OSError):
            atomic_write(file_path, "Test content")
    
    # Check that no temp files are left behind
    temp_files = list(tmp_path.glob(".test.txt.tmp.*"))
    assert len(temp_files) == 0


def test_atomic_write_preserves_on_crash(tmp_path):
    """Test that existing file is preserved if atomic_write crashes mid-operation."""
    file_path = tmp_path / "test.txt"
    original_content = "Original content"
    
    # Write initial content
    file_path.write_text(original_content)
    
    # Simulate crash during write (by patching os.replace to fail)
    import unittest.mock as mock
    
    with mock.patch("os.replace", side_effect=OSError("Simulated crash")):
        with pytest.raises(OSError):
            atomic_write(file_path, "New content")
    
    # Original file should still exist with original content
    assert file_path.exists()
    assert file_path.read_text() == original_content


def test_atomic_write_with_empty_content(tmp_path):
    """Test that atomic_write handles empty content."""
    file_path = tmp_path / "empty.txt"
    
    atomic_write(file_path, "")
    
    assert file_path.exists()
    assert file_path.read_text() == ""


def test_atomic_write_with_large_content(tmp_path):
    """Test that atomic_write handles large content."""
    file_path = tmp_path / "large.txt"
    content = "x" * 1_000_000  # 1 MB of data
    
    atomic_write(file_path, content)
    
    assert file_path.exists()
    assert file_path.read_text() == content
