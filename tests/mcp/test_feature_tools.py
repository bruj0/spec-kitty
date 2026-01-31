"""
Tests for feature_tools MCP handler.

Tests feature operations routing, parameter validation, and integration
with CLIAdapter.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from specify_cli.mcp.tools.feature_tools import (
    feature_operations_handler,
    FeatureOperation,
    FEATURE_OPERATIONS_SCHEMA,
    _handle_specify,
    _handle_plan,
    _handle_tasks,
    _handle_implement,
    _handle_review,
    _handle_accept
)
from specify_cli.mcp.adapters import OperationResult


class TestFeatureOperationsSchema:
    """Test JSON Schema validation."""
    
    def test_schema_has_required_fields(self):
        """Schema should require project_path and operation."""
        assert "required" in FEATURE_OPERATIONS_SCHEMA
        assert "project_path" in FEATURE_OPERATIONS_SCHEMA["required"]
        assert "operation" in FEATURE_OPERATIONS_SCHEMA["required"]
    
    def test_schema_defines_operations_enum(self):
        """Schema should enumerate all supported operations."""
        operations_prop = FEATURE_OPERATIONS_SCHEMA["properties"]["operation"]
        assert "enum" in operations_prop
        
        expected_ops = ["specify", "plan", "tasks", "implement", "review", "accept"]
        assert set(operations_prop["enum"]) == set(expected_ops)
    
    def test_schema_defines_arguments_object(self):
        """Schema should allow arguments object for operation-specific params."""
        args_prop = FEATURE_OPERATIONS_SCHEMA["properties"]["arguments"]
        assert args_prop["type"] == "object"


class TestFeatureOperationsHandler:
    """Test main handler routing logic."""
    
    @pytest.fixture
    def mock_project_context(self, tmp_path):
        """Create mock ProjectContext."""
        kittify_dir = tmp_path / ".kittify"
        kittify_dir.mkdir()
        (kittify_dir / "config.yaml").write_text("agents:\n  available: []\n")
        
        # Create missions directory (required by validation)
        missions_dir = kittify_dir / "missions"
        missions_dir.mkdir()
        
        return tmp_path
    
    def test_invalid_operation_returns_error(self, mock_project_context):
        """Handler should return error for invalid operation."""
        result = feature_operations_handler(
            project_path=str(mock_project_context),
            operation="invalid_operation"
        )
        
        assert result["success"] is False
        assert "invalid operation" in result["message"].lower()
    
    def test_invalid_project_path_returns_error(self):
        """Handler should return error for non-existent project."""
        result = feature_operations_handler(
            project_path="/nonexistent/path",
            operation="specify"
        )
        
        assert result["success"] is False
        assert "invalid project path" in result["message"].lower()
    
    @patch("specify_cli.mcp.tools.feature_tools.CLIAdapter")
    def test_specify_operation_routes_correctly(self, mock_adapter_cls, mock_project_context):
        """Specify operation should route to _handle_specify."""
        mock_adapter = MagicMock()
        mock_adapter.create_feature.return_value = OperationResult.success_result(
            message="Feature created",
            data={"feature_slug": "001-test"}
        )
        mock_adapter_cls.return_value = mock_adapter
        
        result = feature_operations_handler(
            project_path=str(mock_project_context),
            operation="specify",
            arguments={"slug": "test", "description": "Test feature"}
        )
        
        assert result["success"] is True
        mock_adapter.create_feature.assert_called_once()
    
    @patch("specify_cli.mcp.tools.feature_tools.CLIAdapter")
    def test_plan_operation_requires_feature_slug(self, mock_adapter_cls, mock_project_context):
        """Plan operation should require feature_slug parameter."""
        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter
        
        result = feature_operations_handler(
            project_path=str(mock_project_context),
            operation="plan",
            feature_slug=None
        )
        
        assert result["success"] is False
        assert "feature_slug" in result["message"].lower()
    
    @patch("specify_cli.mcp.tools.feature_tools.CLIAdapter")
    def test_implement_operation_requires_wp_id(self, mock_adapter_cls, mock_project_context):
        """Implement operation should require wp_id in arguments."""
        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter
        
        result = feature_operations_handler(
            project_path=str(mock_project_context),
            operation="implement",
            feature_slug="001-test",
            arguments={}  # Missing wp_id
        )
        
        assert result["success"] is False
        assert "wp_id" in result["message"].lower()


class TestSpecifyOperation:
    """Test _handle_specify operation."""
    
    def test_missing_slug_returns_error(self):
        """Specify should fail if slug not provided."""
        mock_adapter = Mock()
        result = _handle_specify(mock_adapter, args={})
        
        assert result.success is False
        assert "slug" in result.message.lower()
    
    def test_delegates_to_adapter_create_feature(self):
        """Specify should call adapter.create_feature with correct params."""
        mock_adapter = Mock()
        mock_adapter.create_feature.return_value = OperationResult.success_result(
            message="Feature created"
        )
        
        result = _handle_specify(
            mock_adapter,
            args={"slug": "test-feature", "description": "Test description"}
        )
        
        assert result.success is True
        mock_adapter.create_feature.assert_called_once_with(
            slug="test-feature",
            description="Test description"
        )


class TestPlanOperation:
    """Test _handle_plan operation."""
    
    def test_missing_feature_slug_returns_error(self):
        """Plan should fail if feature_slug not provided."""
        mock_adapter = Mock()
        result = _handle_plan(mock_adapter, feature_slug=None, args={})
        
        assert result.success is False
        assert "feature_slug" in result.message.lower()
    
    def test_delegates_to_adapter_setup_plan(self):
        """Plan should call adapter.setup_plan with feature_slug."""
        mock_adapter = Mock()
        mock_adapter.setup_plan.return_value = OperationResult.success_result(
            message="Plan created"
        )
        
        result = _handle_plan(mock_adapter, feature_slug="001-test", args={})
        
        assert result.success is True
        mock_adapter.setup_plan.assert_called_once_with(feature_slug="001-test")


class TestTasksOperation:
    """Test _handle_tasks operation."""
    
    def test_missing_feature_slug_returns_error(self):
        """Tasks should fail if feature_slug not provided."""
        mock_adapter = Mock()
        result = _handle_tasks(mock_adapter, feature_slug=None, args={})
        
        assert result.success is False
        assert "feature_slug" in result.message.lower()
    
    def test_delegates_to_adapter_create_tasks(self):
        """Tasks should call adapter.create_tasks with feature_slug."""
        mock_adapter = Mock()
        mock_adapter.create_tasks.return_value = OperationResult.success_result(
            message="Tasks created"
        )
        
        result = _handle_tasks(mock_adapter, feature_slug="001-test", args={})
        
        assert result.success is True
        mock_adapter.create_tasks.assert_called_once_with(feature_slug="001-test")


class TestImplementOperation:
    """Test _handle_implement operation."""
    
    def test_missing_feature_slug_returns_error(self):
        """Implement should fail if feature_slug not provided."""
        mock_adapter = Mock()
        result = _handle_implement(mock_adapter, feature_slug=None, args={"wp_id": "WP01"})
        
        assert result.success is False
        assert "feature_slug" in result.message.lower()
    
    def test_missing_wp_id_returns_error(self):
        """Implement should fail if wp_id not provided."""
        mock_adapter = Mock()
        result = _handle_implement(mock_adapter, feature_slug="001-test", args={})
        
        assert result.success is False
        assert "wp_id" in result.message.lower()
    
    def test_delegates_to_adapter_create_worktree(self):
        """Implement should call adapter.create_worktree with correct params."""
        mock_adapter = Mock()
        mock_adapter.create_worktree.return_value = OperationResult.success_result(
            message="Worktree created"
        )
        
        result = _handle_implement(
            mock_adapter,
            feature_slug="001-test",
            args={"wp_id": "WP01", "base_wp": "WP00"}
        )
        
        assert result.success is True
        mock_adapter.create_worktree.assert_called_once_with(
            feature_slug="001-test",
            wp_id="WP01",
            base_wp="WP00"
        )


class TestReviewOperation:
    """Test _handle_review operation."""
    
    def test_missing_feature_slug_returns_error(self):
        """Review should fail if feature_slug not provided."""
        mock_adapter = Mock()
        result = _handle_review(
            mock_adapter,
            feature_slug=None,
            args={"wp_id": "WP01", "reviewer": "alice", "status": "approved"}
        )
        
        assert result.success is False
        assert "feature_slug" in result.message.lower()
    
    def test_missing_wp_id_returns_error(self):
        """Review should fail if wp_id not provided."""
        mock_adapter = Mock()
        result = _handle_review(
            mock_adapter,
            feature_slug="001-test",
            args={"reviewer": "alice", "status": "approved"}
        )
        
        assert result.success is False
        assert "wp_id" in result.message.lower()
    
    def test_missing_reviewer_returns_error(self):
        """Review should fail if reviewer not provided."""
        mock_adapter = Mock()
        result = _handle_review(
            mock_adapter,
            feature_slug="001-test",
            args={"wp_id": "WP01", "status": "approved"}
        )
        
        assert result.success is False
        assert "reviewer" in result.message.lower()
    
    def test_missing_status_returns_error(self):
        """Review should fail if status not provided."""
        mock_adapter = Mock()
        result = _handle_review(
            mock_adapter,
            feature_slug="001-test",
            args={"wp_id": "WP01", "reviewer": "alice"}
        )
        
        assert result.success is False
        assert "status" in result.message.lower()
    
    def test_delegates_to_adapter_add_history(self):
        """Review should add history entry via adapter."""
        mock_adapter = Mock()
        mock_adapter.add_history.return_value = OperationResult.success_result(
            message="History added"
        )
        
        result = _handle_review(
            mock_adapter,
            feature_slug="001-test",
            args={
                "wp_id": "WP01",
                "reviewer": "alice",
                "status": "approved",
                "comments": "Looks good"
            }
        )
        
        assert result.success is True
        mock_adapter.add_history.assert_called_once()
        call_args = mock_adapter.add_history.call_args
        assert call_args[1]["feature_slug"] == "001-test"
        assert call_args[1]["task_id"] == "WP01"
        assert "alice" in call_args[1]["note"]
        assert "approved" in call_args[1]["note"]


class TestAcceptOperation:
    """Test _handle_accept operation."""
    
    def test_missing_feature_slug_returns_error(self):
        """Accept should fail if feature_slug not provided."""
        mock_adapter = Mock()
        result = _handle_accept(mock_adapter, feature_slug=None, args={})
        
        assert result.success is False
        assert "feature_slug" in result.message.lower()
    
    def test_returns_placeholder_message(self):
        """Accept should return placeholder (not yet implemented)."""
        mock_adapter = Mock()
        result = _handle_accept(mock_adapter, feature_slug="001-test", args={})
        
        assert result.success is True
        assert "not_implemented" in result.data.get("status", "")
        assert len(result.warnings) > 0
    
    def test_respects_merge_strategy_argument(self):
        """Accept should include merge_strategy in result data."""
        mock_adapter = Mock()
        result = _handle_accept(
            mock_adapter,
            feature_slug="001-test",
            args={"merge_strategy": "squash"}
        )
        
        assert result.data["merge_strategy"] == "squash"


class TestIntegrationWithCLIAdapter:
    """Integration tests with real CLIAdapter (using tmp_path)."""
    
    @pytest.fixture
    def test_project(self, tmp_path):
        """Create minimal test project structure."""
        kittify_dir = tmp_path / ".kittify"
        kittify_dir.mkdir()
        (kittify_dir / "config.yaml").write_text("agents:\n  available: []\n")
        
        # Create missions directory (required by validation)
        missions_dir = kittify_dir / "missions"
        missions_dir.mkdir()
        
        specs_dir = tmp_path / "kitty-specs"
        specs_dir.mkdir()
        
        return tmp_path
    
    @patch("specify_cli.mcp.tools.feature_tools.CLIAdapter")
    def test_specify_creates_feature_structure(self, mock_adapter_cls, test_project):
        """Integration test: specify operation creates feature."""
        from specify_cli.mcp.session.context import ProjectContext
        from specify_cli.mcp.adapters import CLIAdapter
        
        # Setup
        ctx = ProjectContext.from_path(test_project)
        real_adapter = CLIAdapter(ctx)
        mock_adapter_cls.return_value = real_adapter
        
        # Execute
        result = feature_operations_handler(
            project_path=str(test_project),
            operation="specify",
            arguments={"slug": "test-feature", "description": "Test"}
        )
        
        # Verify
        assert result["success"] is True
        # Feature directory should be created (001-test-feature)
        feature_dirs = list((test_project / "kitty-specs").iterdir())
        assert len(feature_dirs) == 1
        assert feature_dirs[0].name.endswith("test-feature")
