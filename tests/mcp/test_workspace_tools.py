"""
Tests for workspace_operations MCP tool.

Covers create_worktree, list_worktrees, and merge operations.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest


@pytest.fixture
def valid_project(tmp_path):
    """Create a valid Spec Kitty project structure."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("agents:\n  available: []\n")
    (kittify / "missions").mkdir()
    return tmp_path


# We test by importing the module directly, avoiding the full server stack
@pytest.fixture
def mock_workspace_operations():
    """Mock workspace_operations without importing FastMCP."""
    with patch.dict("sys.modules", {"fastmcp": MagicMock()}):
        from specify_cli.mcp.tools.workspace_tools import workspace_operations
        return workspace_operations


class TestWorkspaceOperationsValidation:
    """Test parameter validation and error handling."""
    
    def test_missing_project_path(self, mock_workspace_operations):
        """Should reject if project_path not provided."""
        result = mock_workspace_operations(
            project_path="",
            operation="list_worktrees"
        )
        
        assert result["success"] is False
        assert "does not exist" in result["message"].lower() or "empty" in result["message"].lower()
    
    def test_invalid_project_path(self, tmp_path, mock_workspace_operations):
        """Should reject non-existent project path."""
        nonexistent = tmp_path / "does-not-exist"
        
        result = mock_workspace_operations(
            project_path=str(nonexistent),
            operation="list_worktrees"
        )
        
        assert result["success"] is False
        assert "does not exist" in result["message"].lower()
    
    def test_invalid_operation(self, tmp_path, mock_workspace_operations):
        """Should reject unknown operation."""
        # Setup minimal valid project
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available: []\n")
        
        result = mock_workspace_operations(
            project_path=str(tmp_path),
            operation="invalid_operation"
        )
        
        assert result["success"] is False
        assert "unknown operation" in result["message"].lower()
    
    def test_create_worktree_missing_wp_id(self, tmp_path, mock_workspace_operations):
        """Should reject create_worktree without work_package_id."""
        # Setup minimal valid project
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available: []\n")
        
        result = mock_workspace_operations(
            project_path=str(tmp_path),
            operation="create_worktree",
            # Missing work_package_id
        )
        
        assert result["success"] is False
        assert "work_package_id" in result["message"].lower()
    
    def test_merge_missing_feature_slug(self, tmp_path, mock_workspace_operations):
        """Should reject merge without feature_slug."""
        # Setup minimal valid project
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available: []\n")
        
        result = mock_workspace_operations(
            project_path=str(tmp_path),
            operation="merge",
            # Missing feature_slug
        )
        
        assert result["success"] is False
        assert "feature_slug" in result["message"].lower()


class TestListWorktrees:
    """Test list_worktrees operation."""
    
    def test_no_worktrees(self, tmp_path, mock_workspace_operations):
        """Should return empty list when no worktrees exist."""
        # Setup minimal valid project
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available: []\n")
        
        result = mock_workspace_operations(
            project_path=str(tmp_path),
            operation="list_worktrees"
        )
        
        assert result["success"] is True
        assert result["data"]["worktrees"] == []
    
    def test_list_existing_worktrees(self, tmp_path, mock_workspace_operations):
        """Should list worktrees in .worktrees/ directory."""
        # Setup project
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available: []\n")
        
        # Create mock worktrees
        worktrees_dir = tmp_path / ".worktrees"
        worktrees_dir.mkdir()
        
        wt1 = worktrees_dir / "099-feature-WP01"
        wt1.mkdir()
        (wt1 / ".git").write_text("gitdir: ../../.git/worktrees/099-feature-WP01\n")
        
        wt2 = worktrees_dir / "099-feature-WP02"
        wt2.mkdir()
        (wt2 / ".git").write_text("gitdir: ../../.git/worktrees/099-feature-WP02\n")
        
        result = mock_workspace_operations(
            project_path=str(tmp_path),
            operation="list_worktrees"
        )
        
        assert result["success"] is True
        assert len(result["data"]["worktrees"]) == 2
        
        # Check names
        names = [wt["name"] for wt in result["data"]["worktrees"]]
        assert "099-feature-WP01" in names
        assert "099-feature-WP02" in names
    
    def test_ignores_hidden_directories(self, tmp_path, mock_workspace_operations):
        """Should skip hidden directories (starting with .)."""
        # Setup project
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available: []\n")
        
        worktrees_dir = tmp_path / ".worktrees"
        worktrees_dir.mkdir()
        
        # Valid worktree
        wt1 = worktrees_dir / "099-feature-WP01"
        wt1.mkdir()
        (wt1 / ".git").write_text("gitdir: ../../.git/worktrees/099-feature-WP01\n")
        
        # Hidden directory (should be ignored)
        hidden = worktrees_dir / ".hidden"
        hidden.mkdir()
        (hidden / ".git").write_text("gitdir: ../../.git/worktrees/.hidden\n")
        
        result = mock_workspace_operations(
            project_path=str(tmp_path),
            operation="list_worktrees"
        )
        
        assert result["success"] is True
        assert len(result["data"]["worktrees"]) == 1
        assert result["data"]["worktrees"][0]["name"] == "099-feature-WP01"


class TestCreateWorktree:
    """Test create_worktree operation."""
    
    @patch("specify_cli.mcp.tools.workspace_tools.detect_feature_slug")
    @patch("specify_cli.mcp.adapters.cli_adapter.subprocess.run")
    def test_create_worktree_success(self, mock_subprocess, mock_detect, tmp_path, mock_workspace_operations):
        """Should create worktree with git worktree add command."""
        # Setup project
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available: []\n")
        
        # Setup git repo (mock)
        (tmp_path / ".git").mkdir()
        
        # Mock feature detection
        mock_detect.return_value = "099-test-feature"
        
        # Mock successful git worktree creation
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        result = mock_workspace_operations(
            project_path=str(tmp_path),
            operation="create_worktree",
            work_package_id="WP01",
        )
        
        assert result["success"] is True
        assert "WP01" in result["message"]
        assert result["data"]["wp_id"] == "WP01"
        assert "099-test-feature-WP01" in result["data"]["branch_name"]
        
        # Verify git worktree add was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert "git" in call_args[0][0]
        assert "worktree" in call_args[0][0]
        assert "add" in call_args[0][0]
    
    @patch("specify_cli.mcp.adapters.cli_adapter.subprocess.run")
    def test_create_worktree_with_base(self, mock_subprocess, tmp_path, mock_workspace_operations):
        """Should create worktree branching from base_wp."""
        # Setup project
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available: []\n")
        
        (tmp_path / ".git").mkdir()
        
        # Mock successful git worktree creation
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        result = mock_workspace_operations(
            project_path=str(tmp_path),
            operation="create_worktree",
            work_package_id="WP02",
            base_wp="WP01",
            feature_slug="099-test-feature"
        )
        
        assert result["success"] is True
        assert "WP02" in result["message"]
        assert result["data"]["base_branch"] == "099-test-feature-WP01"
        
        # Verify git command used correct base branch
        call_args = mock_subprocess.call_args[0][0]
        assert "099-test-feature-WP01" in call_args
    
    @patch("specify_cli.mcp.adapters.cli_adapter.subprocess.run")
    def test_create_worktree_git_error(self, mock_subprocess, tmp_path, mock_workspace_operations):
        """Should handle git worktree errors gracefully."""
        # Setup project
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available: []\n")
        
        (tmp_path / ".git").mkdir()
        
        # Mock git failure
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            returncode=128,
            cmd=["git", "worktree", "add"],
            stderr="fatal: invalid reference: main"
        )
        
        result = mock_workspace_operations(
            project_path=str(tmp_path),
            operation="create_worktree",
            work_package_id="WP01",
            feature_slug="099-test-feature"
        )
        
        assert result["success"] is False
        assert "failed to create worktree" in result["message"].lower()


class TestMergeOperation:
    """Test merge operation."""
    
    def test_merge_not_implemented_placeholder(self, tmp_path, mock_workspace_operations):
        """Should handle merge operation (placeholder until merge module complete)."""
        # Setup project
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available: []\n")
        
        result = mock_workspace_operations(
            project_path=str(tmp_path),
            operation="merge",
            feature_slug="099-test-feature"
        )
        
        # Should return error with helpful message about merge module
        assert result["success"] is False
        assert "merge" in result["message"].lower()
        # Should mention the merge workflow or that it's not available
        assert any(
            keyword in result["message"].lower()
            for keyword in ["not available", "pending", "placeholder"]
        ) or "merge" in result.get("errors", [""])[0].lower()


class TestIntegrationScenarios:
    """Integration tests combining multiple operations."""
    
    @patch("specify_cli.mcp.tools.workspace_tools.detect_feature_slug")
    @patch("specify_cli.mcp.adapters.cli_adapter.subprocess.run")
    def test_create_and_list_workflow(self, mock_subprocess, mock_detect, tmp_path, mock_workspace_operations):
        """Should create worktree and then list it."""
        # Setup project
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available: []\n")
        
        (tmp_path / ".git").mkdir()
        
        mock_detect.return_value = "099-test-feature"
        
        # Mock successful creation
        def create_worktree_mock(*args, **kwargs):
            # Simulate worktree creation
            worktrees_dir = tmp_path / ".worktrees"
            worktrees_dir.mkdir(exist_ok=True)
            wt = worktrees_dir / "099-test-feature-WP01"
            wt.mkdir(exist_ok=True)
            (wt / ".git").write_text("gitdir: ../../.git/worktrees/099-test-feature-WP01\n")
            return Mock(returncode=0, stdout="", stderr="")
        
        mock_subprocess.side_effect = create_worktree_mock
        
        # Create worktree
        create_result = mock_workspace_operations(
            project_path=str(tmp_path),
            operation="create_worktree",
            work_package_id="WP01"
        )
        
        assert create_result["success"] is True
        
        # List worktrees
        list_result = mock_workspace_operations(
            project_path=str(tmp_path),
            operation="list_worktrees"
        )
        
        assert list_result["success"] is True
        assert len(list_result["data"]["worktrees"]) == 1
        assert list_result["data"]["worktrees"][0]["name"] == "099-test-feature-WP01"


class TestErrorRecovery:
    """Test error handling and recovery scenarios."""
    
    def test_handles_missing_kittify_gracefully(self, tmp_path, mock_workspace_operations):
        """Should provide helpful error when .kittify missing."""
        # No .kittify directory
        result = mock_workspace_operations(
            project_path=str(tmp_path),
            operation="list_worktrees"
        )
        
        assert result["success"] is False
        assert ".kittify" in result["message"] or "invalid project" in result["message"].lower()
    
    def test_handles_exception_in_handler(self, tmp_path, mock_workspace_operations):
        """Should catch and report unexpected exceptions."""
        # Setup minimal project
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available: []\n")
        
        # Trigger exception by passing invalid data that might cause internal error
        with patch("specify_cli.mcp.adapters.cli_adapter.CLIAdapter.list_worktrees") as mock_list:
            mock_list.side_effect = RuntimeError("Unexpected internal error")
            
            result = mock_workspace_operations(
                project_path=str(tmp_path),
                operation="list_worktrees"
            )
            
            assert result["success"] is False
            assert "failed" in result["message"].lower() or "error" in result["message"].lower()
