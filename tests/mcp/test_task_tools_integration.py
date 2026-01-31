"""Integration tests for task operations with full MCP stack."""

import pytest
from pathlib import Path
import tempfile
import shutil

from specify_cli.mcp.tools.task_tools import (
    register_task_operations_tool,
    task_operations_handler,
)


@pytest.fixture
def test_project(tmp_path):
    """Create a complete test project structure."""
    project_path = tmp_path / "test-project"
    project_path.mkdir()
    
    # Create .kittify structure
    kittify_dir = project_path / ".kittify"
    kittify_dir.mkdir()
    (kittify_dir / "config.yaml").write_text("agents:\n  available: [claude]\n")
    
    missions_dir = kittify_dir / "missions"
    missions_dir.mkdir()
    
    locks_dir = kittify_dir / ".locks"
    locks_dir.mkdir()
    
    # Create kitty-specs with feature
    specs_dir = project_path / "kitty-specs"
    specs_dir.mkdir()
    
    feature_slug = "001-test-feature"
    feature_dir = specs_dir / feature_slug
    feature_dir.mkdir()
    
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    
    # Create sample tasks
    tasks = [
        ("WP01", "planned", []),
        ("WP02", "doing", ["WP01"]),
        ("WP03", "for_review", ["WP02"]),
    ]
    
    for wp_id, lane, deps in tasks:
        task_content = f"""---
work_package_id: {wp_id}
title: Test Task {wp_id}
lane: {lane}
dependencies: {deps}
subtasks: []
assignee: ""
agent: ""
review_status: ""
history:
  - timestamp: "2026-01-31T00:00:00Z"
    lane: {lane}
    agent: system
    shell_pid: ""
    action: "Task created"
---

# Work Package: {wp_id}

Task content here.
"""
        task_file = tasks_dir / f"{wp_id}-test-task.md"
        task_file.write_text(task_content)
    
    return {
        "project_path": project_path,
        "feature_slug": feature_slug,
        "tasks_dir": tasks_dir,
    }


class TestEndToEndTaskWorkflow:
    """Test complete task workflow from list to done."""
    
    def test_complete_workflow(self, test_project):
        """Test moving task through complete workflow."""
        project_path = str(test_project["project_path"])
        feature_slug = test_project["feature_slug"]
        
        # 1. List all tasks initially
        result = task_operations_handler(
            project_path=project_path,
            operation="list_tasks",
            feature_slug=feature_slug
        )
        assert result["success"] is True
        assert len(result["data"]["tasks"]) == 3
        
        # 2. Query status of WP01 (should be planned)
        result = task_operations_handler(
            project_path=project_path,
            operation="query_status",
            feature_slug=feature_slug,
            task_id="WP01"
        )
        assert result["success"] is True
        assert result["data"]["lane"] == "planned"
        
        # 3. Move WP01 to doing
        result = task_operations_handler(
            project_path=project_path,
            operation="move_task",
            feature_slug=feature_slug,
            task_id="WP01",
            lane="doing",
            note="Starting implementation"
        )
        assert result["success"] is True
        
        # 4. Add history to WP01
        result = task_operations_handler(
            project_path=project_path,
            operation="add_history",
            feature_slug=feature_slug,
            task_id="WP01",
            note="Completed subtask 1"
        )
        assert result["success"] is True
        
        # 5. Move WP01 to for_review
        result = task_operations_handler(
            project_path=project_path,
            operation="move_task",
            feature_slug=feature_slug,
            task_id="WP01",
            lane="for_review",
            note="Ready for review"
        )
        assert result["success"] is True
        
        # 6. Move WP01 to done
        result = task_operations_handler(
            project_path=project_path,
            operation="move_task",
            feature_slug=feature_slug,
            task_id="WP01",
            lane="done",
            note="Approved"
        )
        assert result["success"] is True
        
        # 7. Verify final state
        result = task_operations_handler(
            project_path=project_path,
            operation="query_status",
            feature_slug=feature_slug,
            task_id="WP01"
        )
        assert result["success"] is True
        assert result["data"]["lane"] == "done"
        assert result["data"]["is_done"] is True
        
        # 8. List tasks in done lane
        result = task_operations_handler(
            project_path=project_path,
            operation="list_tasks",
            feature_slug=feature_slug,
            lane="done"
        )
        assert result["success"] is True
        assert len(result["data"]["tasks"]) == 1
        assert result["data"]["tasks"][0]["work_package_id"] == "WP01"


class TestErrorHandling:
    """Test error handling in edge cases."""
    
    def test_missing_project_path(self):
        """Test error when project path doesn't exist."""
        result = task_operations_handler(
            project_path="/nonexistent/path",
            operation="list_tasks",
            feature_slug="test-feature"
        )
        assert result["success"] is False
    
    def test_missing_feature(self, test_project):
        """Test error when feature doesn't exist."""
        result = task_operations_handler(
            project_path=str(test_project["project_path"]),
            operation="list_tasks",
            feature_slug="999-nonexistent"
        )
        assert result["success"] is False
    
    def test_invalid_operation(self, test_project):
        """Test error with invalid operation."""
        result = task_operations_handler(
            project_path=str(test_project["project_path"]),
            operation="invalid_op",
            feature_slug=test_project["feature_slug"]
        )
        assert result["success"] is False
        assert "Unknown operation" in result["message"]
    
    def test_missing_required_params(self, test_project):
        """Test error when required params are missing."""
        # move_task requires lane
        result = task_operations_handler(
            project_path=str(test_project["project_path"]),
            operation="move_task",
            feature_slug=test_project["feature_slug"],
            task_id="WP01"
            # Missing lane parameter
        )
        assert result["success"] is False
        assert "Missing required parameters" in result["message"]


class TestLaneFiltering:
    """Test lane filtering in list_tasks operation."""
    
    def test_filter_by_planned(self, test_project):
        """Test filtering tasks by planned lane."""
        result = task_operations_handler(
            project_path=str(test_project["project_path"]),
            operation="list_tasks",
            feature_slug=test_project["feature_slug"],
            lane="planned"
        )
        assert result["success"] is True
        assert len(result["data"]["tasks"]) == 1
        assert result["data"]["tasks"][0]["work_package_id"] == "WP01"
    
    def test_filter_by_doing(self, test_project):
        """Test filtering tasks by doing lane."""
        result = task_operations_handler(
            project_path=str(test_project["project_path"]),
            operation="list_tasks",
            feature_slug=test_project["feature_slug"],
            lane="doing"
        )
        assert result["success"] is True
        assert len(result["data"]["tasks"]) == 1
        assert result["data"]["tasks"][0]["work_package_id"] == "WP02"
    
    def test_filter_by_for_review(self, test_project):
        """Test filtering tasks by for_review lane."""
        result = task_operations_handler(
            project_path=str(test_project["project_path"]),
            operation="list_tasks",
            feature_slug=test_project["feature_slug"],
            lane="for_review"
        )
        assert result["success"] is True
        assert len(result["data"]["tasks"]) == 1
        assert result["data"]["tasks"][0]["work_package_id"] == "WP03"
    
    def test_filter_by_done(self, test_project):
        """Test filtering tasks by done lane (none initially)."""
        result = task_operations_handler(
            project_path=str(test_project["project_path"]),
            operation="list_tasks",
            feature_slug=test_project["feature_slug"],
            lane="done"
        )
        assert result["success"] is True
        assert len(result["data"]["tasks"]) == 0


class TestTaskDependencies:
    """Test dependency tracking in query_status."""
    
    def test_task_with_no_dependencies(self, test_project):
        """Test querying task with no dependencies."""
        result = task_operations_handler(
            project_path=str(test_project["project_path"]),
            operation="query_status",
            feature_slug=test_project["feature_slug"],
            task_id="WP01"
        )
        assert result["success"] is True
        assert result["data"]["dependencies"] == []
        assert result["data"]["has_dependencies"] is False
    
    def test_task_with_dependencies(self, test_project):
        """Test querying task with dependencies."""
        result = task_operations_handler(
            project_path=str(test_project["project_path"]),
            operation="query_status",
            feature_slug=test_project["feature_slug"],
            task_id="WP02"
        )
        assert result["success"] is True
        assert result["data"]["dependencies"] == ["WP01"]
        assert result["data"]["has_dependencies"] is True


class TestHistoryTracking:
    """Test activity log history management."""
    
    def test_add_multiple_history_entries(self, test_project):
        """Test adding multiple history entries."""
        project_path = str(test_project["project_path"])
        feature_slug = test_project["feature_slug"]
        
        # Add first history entry
        result1 = task_operations_handler(
            project_path=project_path,
            operation="add_history",
            feature_slug=feature_slug,
            task_id="WP01",
            note="Progress update 1"
        )
        assert result1["success"] is True
        
        # Add second history entry
        result2 = task_operations_handler(
            project_path=project_path,
            operation="add_history",
            feature_slug=feature_slug,
            task_id="WP01",
            note="Progress update 2"
        )
        assert result2["success"] is True
        
        # Verify both entries are in the file
        task_file = test_project["tasks_dir"] / "WP01-test-task.md"
        content = task_file.read_text()
        assert "Progress update 1" in content
        assert "Progress update 2" in content
    
    def test_history_includes_agent(self, test_project):
        """Test that history entries include agent information."""
        project_path = str(test_project["project_path"])
        feature_slug = test_project["feature_slug"]
        
        result = task_operations_handler(
            project_path=project_path,
            operation="add_history",
            feature_slug=feature_slug,
            task_id="WP01",
            note="Test note"
        )
        assert result["success"] is True
        
        # Verify agent is recorded in task file
        task_file = test_project["tasks_dir"] / "WP01-test-task.md"
        content = task_file.read_text()
        assert "mcp-adapter" in content  # Agent should be recorded
