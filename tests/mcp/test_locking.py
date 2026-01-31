"""Tests for file locking and concurrency control."""

import os
import time
import pytest
from pathlib import Path
from multiprocessing import Process

from specify_cli.mcp.session.locking import ResourceLock, LockTimeout


def test_resource_lock_creation(tmp_path):
    """Test basic ResourceLock creation."""
    lock = ResourceLock.for_resource(tmp_path, "test-resource")
    
    assert lock.resource_id == "test-resource"
    assert lock.lock_file == tmp_path / ".lock-test-resource"
    assert lock.timeout_seconds == 300
    assert lock.acquired_at is None
    assert lock.owner_pid is None


def test_resource_lock_timeout_validation(tmp_path):
    """Test that timeout must be positive."""
    with pytest.raises(ValueError, match="timeout_seconds must be positive"):
        ResourceLock(
            resource_id="test",
            lock_file=tmp_path / ".lock-test",
            timeout_seconds=0
        )
    
    with pytest.raises(ValueError, match="timeout_seconds must be positive"):
        ResourceLock(
            resource_id="test",
            lock_file=tmp_path / ".lock-test",
            timeout_seconds=-1
        )


def test_lock_acquisition_succeeds(tmp_path):
    """Test successful lock acquisition."""
    lock = ResourceLock.for_resource(tmp_path, "test-resource")
    
    with lock.acquire():
        assert lock.acquired_at is not None
        assert lock.owner_pid == os.getpid()
        assert lock.lock_file.exists()


def test_lock_release_on_normal_exit(tmp_path):
    """Test that lock is released on normal context manager exit."""
    lock = ResourceLock.for_resource(tmp_path, "test-resource")
    
    with lock.acquire():
        assert lock.lock_file.exists()
    
    # Lock file may still exist but should be releasable
    assert not lock.is_lock_active()


def test_lock_release_on_exception(tmp_path):
    """Test that lock is released even if exception occurs."""
    lock = ResourceLock.for_resource(tmp_path, "test-resource")
    
    try:
        with lock.acquire():
            assert lock.lock_file.exists()
            raise ValueError("Test exception")
    except ValueError:
        pass
    
    # Lock should be released despite exception
    assert not lock.is_lock_active()


def test_concurrent_lock_acquisition_fails(tmp_path):
    """Test that second process cannot acquire lock while first holds it."""
    lock1 = ResourceLock.for_resource(tmp_path, "test-resource", timeout_seconds=1)
    lock2 = ResourceLock.for_resource(tmp_path, "test-resource", timeout_seconds=1)
    
    with lock1.acquire():
        # Second acquisition should timeout
        with pytest.raises(LockTimeout, match="Resource test-resource is locked"):
            with lock2.acquire():
                pass


def test_sequential_lock_acquisition_succeeds(tmp_path):
    """Test that lock can be acquired after being released."""
    lock1 = ResourceLock.for_resource(tmp_path, "test-resource")
    lock2 = ResourceLock.for_resource(tmp_path, "test-resource")
    
    with lock1.acquire():
        assert lock1.owner_pid == os.getpid()
    
    # Second acquisition should succeed after first is released
    with lock2.acquire():
        assert lock2.owner_pid == os.getpid()


def test_stale_lock_detection(tmp_path):
    """Test detection of stale locks."""
    lock = ResourceLock.for_resource(tmp_path, "test-resource", timeout_seconds=1)
    
    # Create a stale lock file
    lock.lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock.lock_file.touch()
    
    # Make it old enough to be stale (2x timeout)
    old_time = time.time() - (lock.timeout_seconds * 2 + 1)
    os.utime(lock.lock_file, (old_time, old_time))
    
    # Should detect and remove stale lock
    assert lock.release_if_stale() is True
    assert not lock.lock_file.exists()


def test_stale_lock_auto_cleanup(tmp_path):
    """Test that stale locks are automatically cleaned up on acquisition."""
    lock1 = ResourceLock.for_resource(tmp_path, "test-resource", timeout_seconds=1)
    
    # Create a stale lock file
    lock1.lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock1.lock_file.touch()
    
    # Make it old enough to be stale
    old_time = time.time() - (lock1.timeout_seconds * 2 + 1)
    os.utime(lock1.lock_file, (old_time, old_time))
    
    # Acquisition should clean up stale lock and succeed
    lock2 = ResourceLock.for_resource(tmp_path, "test-resource", timeout_seconds=1)
    with lock2.acquire():
        assert lock2.owner_pid == os.getpid()


def test_work_package_lock_isolation(tmp_path):
    """Test that WP locks are independent."""
    lock1 = ResourceLock.for_work_package(tmp_path, "WP01")
    lock2 = ResourceLock.for_work_package(tmp_path, "WP02")
    
    with lock1.acquire():
        # lock2 should be acquirable (different resource)
        with lock2.acquire():
            assert lock1.owner_pid == lock2.owner_pid
            assert lock1.resource_id == "WP-WP01"
            assert lock2.resource_id == "WP-WP02"


def test_feature_lock_granularity(tmp_path):
    """Test feature-level lock naming."""
    lock = ResourceLock.for_feature(tmp_path, "025-mcp-server")
    
    assert lock.resource_id == "feature-025-mcp-server"
    assert lock.lock_file == tmp_path / ".lock-feature-025-mcp-server"


def test_config_lock_granularity(tmp_path):
    """Test config file lock naming."""
    lock = ResourceLock.for_config_file(tmp_path, "agent-config")
    
    assert lock.resource_id == "config-agent-config"
    assert lock.lock_file == tmp_path / ".lock-config-agent-config"


def test_config_lock_default_name(tmp_path):
    """Test config lock with default name."""
    lock = ResourceLock.for_config_file(tmp_path)
    
    assert lock.resource_id == "config-config"
    assert lock.lock_file == tmp_path / ".lock-config-config"


def test_lock_directory_created_automatically(tmp_path):
    """Test that lock directory is created if it doesn't exist."""
    lock_dir = tmp_path / "subdir" / ".locks"
    assert not lock_dir.exists()
    
    lock = ResourceLock.for_resource(lock_dir, "test-resource")
    
    with lock.acquire():
        assert lock_dir.exists()
        assert lock.lock_file.exists()


def test_is_lock_active(tmp_path):
    """Test checking if lock is currently active."""
    lock1 = ResourceLock.for_resource(tmp_path, "test-resource")
    lock2 = ResourceLock.for_resource(tmp_path, "test-resource", timeout_seconds=1)
    
    # Initially not active
    assert not lock1.is_lock_active()
    
    # Active while held
    with lock1.acquire():
        assert lock2.is_lock_active()
    
    # Not active after release
    assert not lock1.is_lock_active()


def test_lock_timeout_message(tmp_path):
    """Test that timeout error message is helpful."""
    lock1 = ResourceLock.for_resource(tmp_path, "test-resource", timeout_seconds=1)
    lock2 = ResourceLock.for_resource(tmp_path, "test-resource", timeout_seconds=1)
    
    with lock1.acquire():
        with pytest.raises(LockTimeout) as exc_info:
            with lock2.acquire():
                pass
        
        error_msg = str(exc_info.value)
        assert "test-resource" in error_msg
        assert "locked" in error_msg.lower()
        assert "1s" in error_msg or "1 s" in error_msg


def test_custom_timeout(tmp_path):
    """Test lock with custom timeout."""
    lock = ResourceLock.for_resource(tmp_path, "test-resource", timeout_seconds=60)
    
    assert lock.timeout_seconds == 60


def test_very_short_timeout(tmp_path):
    """Test lock with very short timeout (fail fast)."""
    lock1 = ResourceLock.for_resource(tmp_path, "test-resource")
    lock2 = ResourceLock.for_resource(tmp_path, "test-resource", timeout_seconds=1)
    
    with lock1.acquire():
        start_time = time.time()
        
        with pytest.raises(LockTimeout):
            with lock2.acquire():
                pass
        
        elapsed = time.time() - start_time
        # Should fail quickly (within 2 seconds to account for overhead)
        assert elapsed < 2


def test_release_if_stale_returns_false_for_fresh_lock(tmp_path):
    """Test that release_if_stale returns False for non-stale locks."""
    lock = ResourceLock.for_resource(tmp_path, "test-resource")
    
    with lock.acquire():
        pass
    
    # Lock just released, not stale
    assert lock.release_if_stale() is False


def test_release_if_stale_returns_false_for_nonexistent_lock(tmp_path):
    """Test that release_if_stale returns False when lock doesn't exist."""
    lock = ResourceLock.for_resource(tmp_path, "test-resource")
    
    assert not lock.lock_file.exists()
    assert lock.release_if_stale() is False
