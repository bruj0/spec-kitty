"""Atomic file operations for state persistence."""

import os
import tempfile
from pathlib import Path


def atomic_write(file_path: Path, content: str):
    """
    Write content to file atomically.
    
    Strategy:
    1. Write to temporary file in same directory
    2. fsync to ensure data on disk
    3. Rename to target filename (atomic operation)
    
    This prevents corruption if process crashes during write.
    
    Args:
        file_path: Target file path
        content: String content to write
        
    Raises:
        OSError: If write or rename fails
    """
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temp file in same directory (ensures same filesystem)
    temp_fd, temp_path = tempfile.mkstemp(
        dir=file_path.parent,
        prefix=f".{file_path.name}.tmp."
    )
    
    try:
        # Write content
        os.write(temp_fd, content.encode("utf-8"))
        
        # Ensure data written to disk
        os.fsync(temp_fd)
        
        # Close file descriptor
        os.close(temp_fd)
        
        # Atomic rename
        os.replace(temp_path, file_path)
    except Exception:
        # Clean up temp file on error
        try:
            os.close(temp_fd)
        except Exception:
            pass
        
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        
        raise
