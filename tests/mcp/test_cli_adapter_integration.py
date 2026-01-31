"""Integration tests for CLI adapter with real project fixtures."""

import pytest
from pathlib import Path

from specify_cli.mcp.adapters import CLIAdapter
from specify_cli.mcp.session.context import ProjectContext


@pytest.fixture
def test_project(tmp_path):
    """Create a minimal spec-kitty project for testing."""
    # Create minimal project structure
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    
    (kittify_dir / "config.yaml").write_text("project: test\n")
    
    missions_dir = kittify_dir / "missions"
    missions_dir.mkdir()
    (missions_dir / "test-mission").mkdir()
    
    (tmp_path / "kitty-specs").mkdir()
    
    return tmp_path


@pytest.fixture
def adapter_with_project(test_project):
    """Create CLIAdapter with test project."""
    context = ProjectContext.from_path(test_project)
    return CLIAdapter(context), test_project


def test_end_to_end_feature_workflow(adapter_with_project):
    """Test complete feature creation workflow."""
    adapter, project_path = adapter_with_project
    
    # Create feature
    result = adapter.create_feature("test-feature", "Test description")
    assert result.success
    feature_slug = result.data["feature_slug"]
    
    # Verify feature directory exists
    feature_dir = project_path / "kitty-specs" / feature_slug
    assert feature_dir.exists()
    assert (feature_dir / "tasks").exists()
    
    # Create plan
    result = adapter.setup_plan(feature_slug)
    assert result.success
    assert (feature_dir / "plan.md").exists()
    
    # Create tasks
    result = adapter.create_tasks(feature_slug)
    assert result.success
    assert (feature_dir / "tasks.md").exists()


def test_end_to_end_task_workflow(adapter_with_project):
    """Test complete task management workflow."""
    adapter, project_path = adapter_with_project
    
    # Create feature with task
    feature_slug = "001-test-feature"
    feature_dir = project_path / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    
    # Create task file
    task_file = tasks_dir / "WP01-setup.md"
    task_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Setup Infrastructure\n"
        "lane: planned\n"
        "history: []\n"
        "---\n"
        "\n# WP01 Content\n"
    )
    
    # List tasks
    result = adapter.list_tasks(feature_slug)
    assert result.success
    assert len(result.data["tasks"]) == 1
    
    # Move task
    result = adapter.move_task(feature_slug, "WP01", "doing", "Starting work")
    assert result.success
    
    # Verify lane changed
    content = task_file.read_text()
    assert "lane: doing" in content or "lane: 'doing'" in content
    
    # Add history
    result = adapter.add_history(feature_slug, "WP01", "Progress update")
    assert result.success
    
    # Verify history added
    content = task_file.read_text()
    assert "Progress update" in content


def test_system_operations(adapter_with_project):
    """Test system validation and mission listing."""
    adapter, project_path = adapter_with_project
    
    # Validate project
    result = adapter.validate_project()
    assert result.success
    
    # Get missions
    result = adapter.get_missions()
    assert result.success
    assert len(result.data["missions"]) >= 1


def test_error_handling_graceful_degradation(adapter_with_project):
    """Test that errors are handled gracefully."""
    adapter, project_path = adapter_with_project
    
    # Try to work with non-existent feature
    result = adapter.list_tasks("nonexistent-feature")
    assert not result.success
    assert len(result.errors) > 0
    assert "not found" in result.message.lower() or "does not exist" in result.message.lower()
