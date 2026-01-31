"""File locking and concurrency control for MCP operations.

This module implements pessimistic file-level locking using the filelock library
to prevent concurrent modifications from multiple MCP clients.
"""

from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from contextlib import contextmanager
import os
import time
import logging

from filelock import FileLock, Timeout as FilelockTimeout

logger = logging.getLogger(__name__)


class LockTimeout(Exception):
    """Raised when lock acquisition times out."""
    pass


@dataclass
class ResourceLock:
    """Represents a pessimistic lock on a project resource.
    
    Attributes:
        resource_id: Unique identifier for the resource (e.g., "WP-WP01", "feature-025-mcp-server")
        lock_file: Path to the lock file in .kittify/.locks/
        timeout_seconds: Maximum time to wait for lock acquisition (default: 300s = 5 minutes)
        acquired_at: ISO timestamp when lock was acquired
        owner_pid: Process ID that owns the lock
    """
    
    resource_id: str
    lock_file: Path
    timeout_seconds: int = 300  # 5 minutes default
    acquired_at: Optional[str] = field(default=None, init=False)
    owner_pid: Optional[int] = field(default=None, init=False)
    
    def __post_init__(self):
        """Validate timeout is positive."""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
    
    @classmethod
    def for_resource(
        cls,
        lock_dir: Path,
        resource_id: str,
        timeout_seconds: int = 300
    ) -> "ResourceLock":
        """Create ResourceLock for a specific resource.
        
        Args:
            lock_dir: Directory where lock files are stored (e.g., .kittify/.locks/)
            resource_id: Unique identifier for the resource
            timeout_seconds: Maximum time to wait for lock acquisition
            
        Returns:
            ResourceLock instance configured for the resource
        """
        lock_file = lock_dir / f".lock-{resource_id}"
        
        return cls(
            resource_id=resource_id,
            lock_file=lock_file,
            timeout_seconds=timeout_seconds
        )
    
    @classmethod
    def for_work_package(
        cls,
        lock_dir: Path,
        wp_id: str,
        timeout_seconds: int = 300
    ) -> "ResourceLock":
        """Create lock for a work package.
        
        Args:
            lock_dir: Directory where lock files are stored
            wp_id: Work package ID (e.g., "WP01")
            timeout_seconds: Maximum time to wait for lock acquisition
            
        Returns:
            ResourceLock instance for the work package
        """
        return cls.for_resource(lock_dir, f"WP-{wp_id}", timeout_seconds)
    
    @classmethod
    def for_feature(
        cls,
        lock_dir: Path,
        feature_slug: str,
        timeout_seconds: int = 300
    ) -> "ResourceLock":
        """Create lock for an entire feature.
        
        Args:
            lock_dir: Directory where lock files are stored
            feature_slug: Feature slug (e.g., "025-mcp-server")
            timeout_seconds: Maximum time to wait for lock acquisition
            
        Returns:
            ResourceLock instance for the feature
        """
        return cls.for_resource(lock_dir, f"feature-{feature_slug}", timeout_seconds)
    
    @classmethod
    def for_config_file(
        cls,
        lock_dir: Path,
        config_name: str = "config",
        timeout_seconds: int = 300
    ) -> "ResourceLock":
        """Create lock for a configuration file.
        
        Args:
            lock_dir: Directory where lock files are stored
            config_name: Name of the config file (default: "config")
            timeout_seconds: Maximum time to wait for lock acquisition
            
        Returns:
            ResourceLock instance for the config file
        """
        return cls.for_resource(lock_dir, f"config-{config_name}", timeout_seconds)
    
    def is_lock_active(self) -> bool:
        """Check if lock is held by an active process.
        
        Returns:
            True if lock is currently held, False otherwise
        """
        if not self.lock_file.exists():
            return False
        
        # Try to acquire with very short timeout to check if locked
        try:
            lock = FileLock(self.lock_file, timeout=0.1)
            with lock.acquire(timeout=0.1):
                # Successfully acquired, was not locked
                return False
        except FilelockTimeout:
            # Could not acquire, is locked
            return True
    
    def release_if_stale(self) -> bool:
        """Check if lock is stale (owning process no longer exists).
        
        If stale, remove lock file. A lock is considered stale if it's older
        than 2x the timeout period.
        
        Returns:
            True if lock was stale and removed, False otherwise
        """
        if not self.lock_file.exists():
            return False
        
        # Check if lock file is old enough to be considered stale
        lock_age = time.time() - self.lock_file.stat().st_mtime
        
        # If lock older than 2x timeout, consider stale
        if lock_age > (self.timeout_seconds * 2):
            try:
                self.lock_file.unlink()
                logger.warning(
                    f"Removed stale lock for {self.resource_id} "
                    f"(age: {lock_age:.1f}s, threshold: {self.timeout_seconds * 2}s)"
                )
                return True
            except OSError as e:
                logger.error(f"Failed to remove stale lock {self.lock_file}: {e}")
                return False
        
        return False
    
    @contextmanager
    def acquire(self):
        """Acquire lock with automatic stale lock cleanup.
        
        This is a context manager that:
        1. Checks for and cleans up stale locks
        2. Attempts to acquire the lock with the configured timeout
        3. Records acquisition metadata (timestamp, PID)
        4. Automatically releases the lock on exit
        
        Raises:
            LockTimeout: If lock cannot be acquired within timeout period
            
        Example:
            >>> lock = ResourceLock.for_work_package(lock_dir, "WP01")
            >>> with lock.acquire():
            ...     # Do work with exclusive access to WP01
            ...     pass
        """
        # Check for stale lock before attempting acquisition
        if self.release_if_stale():
            logger.warning(f"Cleaned up stale lock for {self.resource_id}")
        
        # Ensure lock directory exists
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create filelock instance
        lock = FileLock(self.lock_file, timeout=self.timeout_seconds)
        
        try:
            with lock.acquire(timeout=self.timeout_seconds):
                # Record acquisition metadata
                self.acquired_at = datetime.now(timezone.utc).isoformat()
                self.owner_pid = os.getpid()
                
                logger.debug(
                    f"Lock acquired for {self.resource_id} "
                    f"(PID: {self.owner_pid}, timeout: {self.timeout_seconds}s)"
                )
                
                yield self
                
                logger.debug(f"Lock released for {self.resource_id}")
        except FilelockTimeout:
            raise LockTimeout(
                f"Resource {self.resource_id} is locked. "
                f"Another process is using this resource. "
                f"Retry in a moment or increase timeout (current: {self.timeout_seconds}s)."
            )

