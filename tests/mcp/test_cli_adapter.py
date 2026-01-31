"""Contract tests for CLI adapter."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from specify_cli.mcp.adapters import CLIAdapter, OperationResult
from specify_cli.mcp.session.context import ProjectContext


@pytest.fixture
def mock_project_context(tmp_path):
    """Create mock ProjectContext for testing."""
    # Create minimal project structure
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    
    (kittify_dir / "config.yaml").write_text("project: test\n")
    (kittify_dir / "missions").mkdir()
    
    return ProjectContext.from_path(tmp_path)


@pytest.fixture
def adapter(mock_project_context):
    """Create CLIAdapter instance."""
    return CLIAdapter(mock_project_context)


class TestFeatureOperations:
    """Test feature operation adapters (T022)."""
    
    def test_create_feature_uses_core_functions(self, adapter, tmp_path):
        """Verify adapter uses core worktree functions."""
        # Create minimal project structure
        (tmp_path / "kitty-specs").mkdir()
        
        result = adapter.create_feature("test-feature", "Test description")
        
        assert result.success
        assert "001-test-feature" in result.message
        assert result.data["description"] == "Test description"
        
        # Verify feature directory created
        feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
        assert feature_dir.exists()
        assert (feature_dir / "tasks").exists()
        assert (feature_dir / "checklists").exists()
        assert (feature_dir / "research").exists()
    
    def test_setup_plan_creates_file(self, adapter, tmp_path):
        """Verify plan generation creates plan.md."""
        # Create feature directory first
        feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True)
        
        result = adapter.setup_plan("001-test-feature")
        
        assert result.success
        assert "001-test-feature" in result.message
        assert (feature_dir / "plan.md").exists()
    
    def test_create_tasks_creates_file(self, adapter, tmp_path):
        """Verify task generation creates tasks.md."""
        # Create feature directory first
        feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True)
        
        result = adapter.create_tasks("001-test-feature")
        
        assert result.success
        assert (feature_dir / "tasks.md").exists()
        assert (feature_dir / "tasks").exists()


class TestTaskOperations:
    """Test task operation adapters (T023)."""
    
    def test_list_tasks_reads_frontmatter(self, adapter, tmp_path):
        """Verify task listing reads WP files."""
        # Create feature with task files
        feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        
        # Create sample task file
        task_file = tasks_dir / "WP01-setup.md"
        task_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "title: Setup Infrastructure\n"
            "lane: planned\n"
            "---\n"
            "\n# WP01 Content\n"
        )
        
        result = adapter.list_tasks("001-test-feature")
        
        assert result.success
        assert len(result.data["tasks"]) == 1
        assert result.data["tasks"][0]["work_package_id"] == "WP01"
        assert result.data["tasks"][0]["lane"] == "planned"
    
    def test_list_tasks_filters_by_lane(self, adapter, tmp_path):
        """Verify lane filtering works."""
        # Create feature with task files
        feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        
        # Create tasks in different lanes
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: Task 1\nlane: planned\n---\n"
        )
        (tasks_dir / "WP02.md").write_text(
            "---\nwork_package_id: WP02\ntitle: Task 2\nlane: doing\n---\n"
        )
        
        result = adapter.list_tasks("001-test-feature", lane="doing")
        
        assert result.success
        assert len(result.data["tasks"]) == 1
        assert result.data["tasks"][0]["work_package_id"] == "WP02"
    
    def test_move_task_updates_frontmatter(self, adapter, tmp_path):
        """Verify task movement updates frontmatter."""
        # Create feature with task file
        feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        
        task_file = tasks_dir / "WP01-setup.md"
        task_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "title: Setup\n"
            "lane: planned\n"
            "history: []\n"
            "---\n"
            "\n# Content\n"
        )
        
        result = adapter.move_task("001-test-feature", "WP01", "doing", "Starting work")
        
        assert result.success
        assert result.data["old_lane"] == "planned"
        assert result.data["new_lane"] == "doing"
        
        # Verify file updated
        content = task_file.read_text()
        assert "lane: doing" in content or "lane: 'doing'" in content
    
    def test_add_history_appends_entry(self, adapter, tmp_path):
        """Verify history addition works."""
        # Create feature with task file
        feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        
        task_file = tasks_dir / "WP01-setup.md"
        task_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "title: Setup\n"
            "lane: planned\n"
            "history: []\n"
            "---\n"
            "\n# Content\n"
        )
        
        result = adapter.add_history("001-test-feature", "WP01", "Progress update")
        
        assert result.success
        
        # Verify history added
        content = task_file.read_text()
        assert "Progress update" in content


class TestWorkspaceOperations:
    """Test workspace operation adapters (T024)."""
    
    def test_create_worktree_basic(self, adapter, tmp_path, monkeypatch):
        """Verify worktree creation uses git commands."""
        import subprocess
        called = []
        
        def mock_run(*args, **kwargs):
            called.append((args, kwargs))
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")
        
        monkeypatch.setattr("subprocess.run", mock_run)
        
        result = adapter.create_worktree("001-test-feature", "WP01")
        
        assert result.success
        assert len(called) == 1
        assert "git" in called[0][0][0]
        assert "worktree" in called[0][0][0]
    
    def test_list_worktrees_empty_directory(self, adapter):
        """Verify worktree listing handles missing directory."""
        result = adapter.list_worktrees()
        
        assert result.success
        assert result.data["worktrees"] == []
    
    def test_list_worktrees_finds_directories(self, adapter, tmp_path):
        """Verify worktree listing finds valid worktrees."""
        # Create worktrees directory with valid worktree
        worktrees_dir = tmp_path / ".worktrees"
        worktrees_dir.mkdir()
        
        wp_dir = worktrees_dir / "001-test-feature-WP01"
        wp_dir.mkdir()
        (wp_dir / ".git").write_text("gitdir: ../../.git/worktrees/001-test-feature-WP01")
        
        result = adapter.list_worktrees()
        
        assert result.success
        assert len(result.data["worktrees"]) == 1
        assert result.data["worktrees"][0]["name"] == "001-test-feature-WP01"


class TestSystemOperations:
    """Test system operation adapters (T025)."""
    
    def test_validate_project_success(self, adapter, tmp_path):
        """Verify project validation delegates to context."""
        # Create required directories
        (tmp_path / "kitty-specs").mkdir()
        
        result = adapter.validate_project()
        
        assert result.success
    
    def test_validate_project_failure(self, adapter):
        """Verify validation detects missing directories."""
        # kitty-specs doesn't exist in tmp_path
        result = adapter.validate_project()
        
        assert not result.success
        assert "kitty-specs" in str(result.errors)
    
    def test_get_missions_empty(self, adapter):
        """Verify mission listing handles empty directory."""
        result = adapter.get_missions()
        
        assert result.success
        assert result.data["missions"] == []


class TestErrorHandling:
    """Test error handling decorator (T026)."""
    
    def test_adapter_handles_exceptions(self, adapter):
        """Test that exceptions are caught and converted to errors."""
        # Try to create feature in non-existent directory
        result = adapter.setup_plan("nonexistent-feature")
        
        assert not result.success
        assert "not found" in result.message.lower() or "does not exist" in result.message.lower()
        assert len(result.errors) > 0
    
    def test_missing_directory_handled(self, adapter):
        """Test that missing directories are handled gracefully."""
        result = adapter.list_tasks("nonexistent-feature")
        
        assert not result.success
        assert "not found" in result.message.lower() or "does not exist" in result.message.lower()


class TestOperationResult:
    """Test OperationResult dataclass (T020)."""
    
    def test_success_result_creation(self):
        """Test creating success results."""
        result = OperationResult.success_result(
            message="Success",
            data={"key": "value"},
            artifacts=[Path("/fake/file")]
        )
        
        assert result.success
        assert result.message == "Success"
        assert result.data["key"] == "value"
        assert len(result.artifacts) == 1
    
    def test_error_result_creation(self):
        """Test creating error results."""
        result = OperationResult.error_result(
            message="Failed",
            errors=["error1", "error2"]
        )
        
        assert not result.success
        assert result.message == "Failed"
        assert len(result.errors) == 2
    
    def test_to_dict_serialization(self):
        """Test dictionary serialization."""
        result = OperationResult(
            success=True,
            message="Test",
            data={"key": "value"},
            artifacts=[Path("/fake/file")],
            errors=[],
            warnings=["warning"]
        )
        
        d = result.to_dict()
        
        assert d["success"] is True
        assert d["message"] == "Test"
        assert d["data"]["key"] == "value"
        assert d["artifacts"][0] == "/fake/file"  # Path converted to string
        assert len(d["warnings"]) == 1
