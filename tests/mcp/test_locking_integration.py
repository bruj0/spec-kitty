"""Integration tests for locking with ProjectContext."""

from pathlib import Path
import pytest
import yaml

from specify_cli.mcp.session import ProjectContext, ResourceLock, LockTimeout


def test_lock_with_project_context(tmp_path):
    """Test that locks can be created using ProjectContext's lock_dir."""
    # Setup a minimal project structure
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    
    config_file = kittify_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "project_name": "test-project",
        "mission": "software-dev",
        "version": "0.13.0"
    }))
    
    (kittify_dir / "missions").mkdir()
    
    # Create project context
    ctx = ProjectContext.from_path(tmp_path)
    
    # Create lock using context's lock directory
    lock = ResourceLock.for_work_package(ctx.lock_dir, "WP01")
    
    # Verify lock directory path
    assert ctx.lock_dir == kittify_dir
    
    # Acquire and verify
    with lock.acquire():
        assert lock.owner_pid is not None
        assert lock.lock_file.exists()
        assert lock.lock_file.parent == ctx.lock_dir


def test_multiple_clients_different_wps(tmp_path):
    """Test that multiple clients can work on different WPs simultaneously."""
    # Setup project
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    
    config_file = kittify_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "project_name": "test-project",
        "mission": "software-dev",
        "version": "0.13.0"
    }))
    
    (kittify_dir / "missions").mkdir()
    
    ctx = ProjectContext.from_path(tmp_path)
    
    # Create locks for different WPs
    lock_wp01 = ResourceLock.for_work_package(ctx.lock_dir, "WP01")
    lock_wp02 = ResourceLock.for_work_package(ctx.lock_dir, "WP02")
    
    # Both should be acquirable simultaneously
    with lock_wp01.acquire():
        with lock_wp02.acquire():
            assert lock_wp01.resource_id == "WP-WP01"
            assert lock_wp02.resource_id == "WP-WP02"


def test_lock_prevents_concurrent_wp_access(tmp_path):
    """Test that lock prevents concurrent access to the same WP."""
    # Setup project
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    
    config_file = kittify_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "project_name": "test-project",
        "mission": "software-dev",
        "version": "0.13.0"
    }))
    
    (kittify_dir / "missions").mkdir()
    
    ctx = ProjectContext.from_path(tmp_path)
    
    # Create two locks for same WP
    lock1 = ResourceLock.for_work_package(ctx.lock_dir, "WP01", timeout_seconds=1)
    lock2 = ResourceLock.for_work_package(ctx.lock_dir, "WP01", timeout_seconds=1)
    
    # First client acquires
    with lock1.acquire():
        # Second client should timeout
        with pytest.raises(LockTimeout):
            with lock2.acquire():
                pass
