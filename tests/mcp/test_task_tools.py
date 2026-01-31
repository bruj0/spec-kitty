"""Tests for task operations MCP tools."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import shutil

from specify_cli.mcp.tools.task_tools import (
    task_operations_handler,
    _query_task_status,
    TASK_OPERATIONS_SCHEMA,
)
from specify_cli.mcp.adapters import OperationResult, CLIAdapter
from specify_cli.mcp.session.context import ProjectContext
from specify_cli.mcp.session.locking import ResourceLock, LockTimeout


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary Spec Kitty project structure."""
    # Create project structure
    project_path = tmp_path / "test-project"
    project_path.mkdir()
    
    # Create .kittify directory
    kittify_dir = project_path / ".kittify"
    kittify_dir.mkdir()
    (kittify_dir / "config.yaml").write_text("agents:\n  available: [claude]\n")
    
    # Create missions directory
    missions_dir = kittify_dir / "missions"
    missions_dir.mkdir()
    
    # Create locks directory
    locks_dir = kittify_dir / ".locks"
    locks_dir.mkdir()
    
    # Create kitty-specs directory
    specs_dir = project_path / "kitty-specs"
    specs_dir.mkdir()
    
    # Create test feature
    feature_slug = "099-test-feature"
    feature_dir = specs_dir / feature_slug
    feature_dir.mkdir()
    
    # Create tasks directory with sample tasks
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    
    # Create WP01 task file
    wp01_content = """---
work_package_id: WP01
title: Test Task One
lane: planned
dependencies: []
subtasks:
  - T001
  - T002
assignee: ""
agent: ""
review_status: ""
history:
  - timestamp: "2026-01-31T00:00:00Z"
    lane: planned
    agent: system
    shell_pid: ""
    action: "Task created"
---

# Work Package: WP01 - Test Task One

Test task content here.
"""
    (tasks_dir / "WP01-test-task-one.md").write_text(wp01_content)
    
    # Create WP02 task file
    wp02_content = """---
work_package_id: WP02
title: Test Task Two
lane: doing
dependencies:
  - WP01
subtasks:
  - T003
assignee: "test-agent"
agent: "claude"
review_status: ""
history:
  - timestamp: "2026-01-31T00:00:00Z"
    lane: planned
    agent: system
    shell_pid: ""
    action: "Task created"
  - timestamp: "2026-01-31T01:00:00Z"
    lane: doing
    agent: claude
    shell_pid: "12345"
    action: "Started implementation"
---

# Work Package: WP02 - Test Task Two

Test task content here.
"""
    (tasks_dir / "WP02-test-task-two.md").write_text(wp02_content)
    
    # Create WP03 task file
    wp03_content = """---
work_package_id: WP03
title: Test Task Three
lane: done
dependencies: []
subtasks: []
assignee: ""
agent: ""
review_status: "approved"
history:
  - timestamp: "2026-01-31T00:00:00Z"
    lane: planned
    agent: system
    shell_pid: ""
    action: "Task created"
  - timestamp: "2026-01-31T02:00:00Z"
    lane: done
    agent: system
    shell_pid: ""
    action: "Task completed"
---

# Work Package: WP03 - Test Task Three

Test task content here.
"""
    (tasks_dir / "WP03-test-task-three.md").write_text(wp03_content)
    
    return {
        "project_path": project_path,
        "feature_slug": feature_slug,
        "tasks_dir": tasks_dir,
    }


class TestListTasks:
    """Tests for list_tasks operation."""
    
    def test_list_all_tasks(self, temp_project):
        """Test listing all tasks without lane filter."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="list_tasks",
            feature_slug=temp_project["feature_slug"]
        )
        
        assert result["success"] is True
        assert len(result["data"]["tasks"]) == 3
        
        # Verify tasks are sorted by work_package_id
        task_ids = [t["work_package_id"] for t in result["data"]["tasks"]]
        assert task_ids == ["WP01", "WP02", "WP03"]
    
    def test_list_tasks_by_lane(self, temp_project):
        """Test listing tasks filtered by lane."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="list_tasks",
            feature_slug=temp_project["feature_slug"],
            lane="doing"
        )
        
        assert result["success"] is True
        assert len(result["data"]["tasks"]) == 1
        assert result["data"]["tasks"][0]["work_package_id"] == "WP02"
        assert result["data"]["tasks"][0]["lane"] == "doing"
    
    def test_list_tasks_missing_feature_slug(self, temp_project):
        """Test error when feature_slug is missing."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="list_tasks"
        )
        
        assert result["success"] is False
        assert "feature_slug" in result["message"]
    
    def test_list_tasks_invalid_project(self):
        """Test error when project path is invalid."""
        result = task_operations_handler(
            project_path="/nonexistent/path",
            operation="list_tasks",
            feature_slug="test-feature"
        )
        
        assert result["success"] is False


class TestMoveTask:
    """Tests for move_task operation."""
    
    def test_move_task_to_doing(self, temp_project):
        """Test moving task from planned to doing."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="move_task",
            feature_slug=temp_project["feature_slug"],
            task_id="WP01",
            lane="doing",
            note="Starting implementation"
        )
        
        assert result["success"] is True
        assert result["data"]["task_id"] == "WP01"
        assert result["data"]["old_lane"] == "planned"
        assert result["data"]["new_lane"] == "doing"
        
        # Verify task file was updated
        task_file = temp_project["tasks_dir"] / "WP01-test-task-one.md"
        content = task_file.read_text()
        assert "lane: doing" in content
        assert "Starting implementation" in content
    
    def test_move_task_missing_parameters(self, temp_project):
        """Test error when required parameters are missing."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="move_task",
            feature_slug=temp_project["feature_slug"],
            task_id="WP01"
            # Missing lane
        )
        
        assert result["success"] is False
        assert "Missing required parameters" in result["message"]
    
    def test_move_task_nonexistent(self, temp_project):
        """Test error when task doesn't exist."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="move_task",
            feature_slug=temp_project["feature_slug"],
            task_id="WP99",
            lane="doing"
        )
        
        assert result["success"] is False
        assert "not found" in result["message"]
    
    @pytest.mark.timeout(10)
    def test_move_task_with_locking(self, temp_project):
        """Test that move_task uses locking correctly."""
        # This test verifies that locking is used (not testing lock timeout)
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="move_task",
            feature_slug=temp_project["feature_slug"],
            task_id="WP01",
            lane="doing"
        )
        
        assert result["success"] is True
        
        # Verify no lock file remains after operation
        lock_dir = temp_project["project_path"] / ".kittify" / ".locks"
        lock_file = lock_dir / ".lock-WP-WP01"
        assert not lock_file.exists(), "Lock should be released after operation"


class TestAddHistory:
    """Tests for add_history operation."""
    
    def test_add_history_entry(self, temp_project):
        """Test adding history entry to task."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="add_history",
            feature_slug=temp_project["feature_slug"],
            task_id="WP01",
            note="Progress update: completed T001"
        )
        
        assert result["success"] is True
        assert result["data"]["task_id"] == "WP01"
        
        # Verify history was added to task file
        task_file = temp_project["tasks_dir"] / "WP01-test-task-one.md"
        content = task_file.read_text()
        assert "Progress update: completed T001" in content
        assert "mcp-adapter" in content  # Agent should be recorded
    
    def test_add_history_missing_note(self, temp_project):
        """Test error when note is missing."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="add_history",
            feature_slug=temp_project["feature_slug"],
            task_id="WP01"
            # Missing note
        )
        
        assert result["success"] is False
        assert "Missing required parameters" in result["message"]
    
    def test_add_history_nonexistent_task(self, temp_project):
        """Test error when task doesn't exist."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="add_history",
            feature_slug=temp_project["feature_slug"],
            task_id="WP99",
            note="Test note"
        )
        
        assert result["success"] is False
        assert "not found" in result["message"]


class TestQueryStatus:
    """Tests for query_status operation."""
    
    def test_query_planned_task(self, temp_project):
        """Test querying status of planned task."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="query_status",
            feature_slug=temp_project["feature_slug"],
            task_id="WP01"
        )
        
        assert result["success"] is True
        data = result["data"]
        assert data["task_id"] == "WP01"
        assert data["title"] == "Test Task One"
        assert data["lane"] == "planned"
        assert data["dependencies"] == []
        assert data["subtasks"] == ["T001", "T002"]
        assert data["is_done"] is False
        assert data["has_dependencies"] is False
    
    def test_query_doing_task_with_dependencies(self, temp_project):
        """Test querying task in doing lane with dependencies."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="query_status",
            feature_slug=temp_project["feature_slug"],
            task_id="WP02"
        )
        
        assert result["success"] is True
        data = result["data"]
        assert data["task_id"] == "WP02"
        assert data["lane"] == "doing"
        assert data["dependencies"] == ["WP01"]
        assert data["has_dependencies"] is True
        assert data["assignee"] == "test-agent"
        assert data["agent"] == "claude"
    
    def test_query_done_task(self, temp_project):
        """Test querying completed task."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="query_status",
            feature_slug=temp_project["feature_slug"],
            task_id="WP03"
        )
        
        assert result["success"] is True
        data = result["data"]
        assert data["task_id"] == "WP03"
        assert data["lane"] == "done"
        assert data["is_done"] is True
        assert data["review_status"] == "approved"
    
    def test_query_status_missing_task_id(self, temp_project):
        """Test error when task_id is missing."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="query_status",
            feature_slug=temp_project["feature_slug"]
            # Missing task_id
        )
        
        assert result["success"] is False
        assert "Missing required parameters" in result["message"]
    
    def test_query_status_nonexistent_task(self, temp_project):
        """Test error when task doesn't exist."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="query_status",
            feature_slug=temp_project["feature_slug"],
            task_id="WP99"
        )
        
        assert result["success"] is False
        assert "not found" in result["message"]


class TestOperationRouting:
    """Tests for operation routing and validation."""
    
    def test_unknown_operation(self, temp_project):
        """Test error when operation is not recognized."""
        result = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="invalid_operation",
            feature_slug=temp_project["feature_slug"]
        )
        
        assert result["success"] is False
        assert "Unknown operation" in result["message"]
    
    def test_invalid_project_path(self):
        """Test error when project path is invalid."""
        result = task_operations_handler(
            project_path="/nonexistent/path",
            operation="list_tasks",
            feature_slug="test-feature"
        )
        
        assert result["success"] is False


class TestJSONSchema:
    """Tests for JSON Schema validation."""
    
    def test_schema_structure(self):
        """Test that schema has required structure."""
        assert TASK_OPERATIONS_SCHEMA["type"] == "object"
        assert "project_path" in TASK_OPERATIONS_SCHEMA["required"]
        assert "operation" in TASK_OPERATIONS_SCHEMA["required"]
        
        # Verify operation enum
        operations = TASK_OPERATIONS_SCHEMA["properties"]["operation"]["enum"]
        assert "list_tasks" in operations
        assert "move_task" in operations
        assert "add_history" in operations
        assert "query_status" in operations
        
        # Verify lane enum
        lanes = TASK_OPERATIONS_SCHEMA["properties"]["lane"]["enum"]
        assert set(lanes) == {"planned", "doing", "for_review", "done"}


class TestConcurrentAccess:
    """Tests for concurrent access and locking behavior."""
    
    @pytest.mark.timeout(10)
    def test_sequential_task_moves(self, temp_project):
        """Test multiple sequential task moves."""
        # Move WP01 to doing
        result1 = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="move_task",
            feature_slug=temp_project["feature_slug"],
            task_id="WP01",
            lane="doing"
        )
        assert result1["success"] is True
        
        # Move WP01 to for_review
        result2 = task_operations_handler(
            project_path=str(temp_project["project_path"]),
            operation="move_task",
            feature_slug=temp_project["feature_slug"],
            task_id="WP01",
            lane="for_review"
        )
        assert result2["success"] is True
        
        # Verify final state
        task_file = temp_project["tasks_dir"] / "WP01-test-task-one.md"
        content = task_file.read_text()
        assert "lane: for_review" in content
