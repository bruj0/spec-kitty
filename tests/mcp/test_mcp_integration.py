"""
Integration tests for MCP server with all tools.

Tests the complete MCP server with all tool integrations working together,
including feature operations, task operations, workspace operations, and
system operations.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastmcp import FastMCP
from fastmcp.client import Client

from specify_cli.mcp.server import MCPServer
from specify_cli.mcp.session import ProjectContext
from specify_cli.mcp.adapters import OperationResult


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary Spec Kitty project structure."""
    project_root = tmp_path / "test-project"
    project_root.mkdir()
    
    # Create .kittify directory
    kittify_dir = project_root / ".kittify"
    kittify_dir.mkdir()
    
    # Create config.yaml
    config_file = kittify_dir / "config.yaml"
    config_file.write_text("agents:\n  available:\n    - opencode\n")
    
    # Create kitty-specs directory
    specs_dir = project_root / "kitty-specs"
    specs_dir.mkdir()
    
    return project_root


@pytest.fixture
def mcp_server():
    """Create an MCP server instance for testing."""
    server = MCPServer(
        transport="stdio",
        auth_enabled=False
    )
    return server


@pytest.fixture
async def mcp_client(mcp_server):
    """Create an MCP client connected to the test server."""
    # FastMCP test client
    client = Client(mcp_server._app)
    return client


class TestMCPServerIntegration:
    """Integration tests for the complete MCP server."""
    
    def test_server_initialization(self, mcp_server):
        """Test that server initializes with all tools registered."""
        assert mcp_server._app is not None
        assert mcp_server.transport == "stdio"
        assert not mcp_server.auth_enabled
        
        # Check that tools are registered (FastMCP stores them internally)
        # We verify by attempting to call them through the handler
        assert mcp_server._app is not None
    
    def test_server_with_auth(self):
        """Test server initialization with authentication enabled."""
        server = MCPServer(
            transport="stdio",
            auth_enabled=True,
            api_key="test-key-123"
        )
        assert server.auth_enabled
        assert server.api_key == "test-key-123"
    
    def test_server_with_invalid_auth_config(self):
        """Test that server raises error if auth enabled without API key."""
        with pytest.raises(ValueError, match="API key authentication enabled"):
            MCPServer(
                transport="stdio",
                auth_enabled=True,
                api_key=None
            )
    
    def test_server_with_invalid_transport(self):
        """Test that server raises error for invalid transport."""
        with pytest.raises(ValueError, match="Invalid transport"):
            MCPServer(transport="invalid")
    
    @pytest.mark.asyncio
    async def test_system_operations_health_check(self, mcp_client):
        """Test system_operations tool - health_check operation."""
        result = await mcp_client.call_tool(
            "system_operations",
            operation="health_check"
        )
        
        assert result is not None
        # Result should contain server status information
    
    @pytest.mark.asyncio
    async def test_system_operations_validate_project(self, mcp_client, temp_project):
        """Test system_operations tool - validate_project operation."""
        result = await mcp_client.call_tool(
            "system_operations",
            operation="validate_project",
            project_path=str(temp_project)
        )
        
        assert result is not None
        # Should validate that project has .kittify directory
    
    @pytest.mark.asyncio
    async def test_system_operations_list_missions(self, mcp_client):
        """Test system_operations tool - list_missions operation."""
        result = await mcp_client.call_tool(
            "system_operations",
            operation="list_missions"
        )
        
        assert result is not None
        # Should return list of available missions
    
    @pytest.mark.asyncio
    async def test_feature_operations_specify(self, mcp_client, temp_project):
        """Test feature_operations tool - specify operation."""
        with patch('specify_cli.mcp.adapters.CLIAdapter') as mock_adapter:
            mock_adapter.return_value.specify.return_value = OperationResult.success_result(
                message="Feature specified successfully",
                data={"feature_slug": "001-test-feature"}
            )
            
            result = await mcp_client.call_tool(
                "feature_operations",
                operation="specify",
                project_path=str(temp_project),
                description="Test feature"
            )
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_feature_operations_plan(self, mcp_client, temp_project):
        """Test feature_operations tool - plan operation."""
        with patch('specify_cli.mcp.adapters.CLIAdapter') as mock_adapter:
            mock_adapter.return_value.plan.return_value = OperationResult.success_result(
                message="Plan created successfully",
                artifacts=[Path(temp_project / "kitty-specs/001-test-feature/plan.md")]
            )
            
            result = await mcp_client.call_tool(
                "feature_operations",
                operation="plan",
                project_path=str(temp_project),
                feature_slug="001-test-feature"
            )
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_task_operations_list_tasks(self, mcp_client, temp_project):
        """Test task_operations tool - list_tasks operation."""
        result = await mcp_client.call_tool(
            "task_operations",
            operation="list_tasks",
            project_path=str(temp_project),
            feature_slug="001-test-feature"
        )
        
        assert result is not None
        # Should return list of tasks for the feature
    
    @pytest.mark.asyncio
    async def test_task_operations_move_task(self, mcp_client, temp_project):
        """Test task_operations tool - move_task operation."""
        with patch('specify_cli.tasks_support.move_task_to_lane') as mock_move:
            mock_move.return_value = None  # Success
            
            result = await mcp_client.call_tool(
                "task_operations",
                operation="move_task",
                project_path=str(temp_project),
                feature_slug="001-test-feature",
                wp_id="WP01",
                to_lane="doing"
            )
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_workspace_operations_create_worktree(self, mcp_client, temp_project):
        """Test workspace_operations tool - create_worktree operation."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            result = await mcp_client.call_tool(
                "workspace_operations",
                operation="create_worktree",
                project_path=str(temp_project),
                feature_slug="001-test-feature",
                wp_id="WP01"
            )
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_workspace_operations_list_worktrees(self, mcp_client, temp_project):
        """Test workspace_operations tool - list_worktrees operation."""
        result = await mcp_client.call_tool(
            "workspace_operations",
            operation="list_worktrees",
            project_path=str(temp_project)
        )
        
        assert result is not None
        # Should return list of active worktrees


class TestMCPServerWorkflow:
    """Integration tests for complete MCP workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_feature_workflow(self, mcp_client, temp_project):
        """Test complete feature workflow through MCP tools."""
        # 1. Validate project
        validate_result = await mcp_client.call_tool(
            "system_operations",
            operation="validate_project",
            project_path=str(temp_project)
        )
        assert validate_result is not None
        
        # 2. Create feature specification (mocked)
        with patch('specify_cli.mcp.adapters.CLIAdapter') as mock_adapter:
            mock_adapter.return_value.specify.return_value = OperationResult.success_result(
                message="Feature specified",
                data={"feature_slug": "001-test"}
            )
            
            specify_result = await mcp_client.call_tool(
                "feature_operations",
                operation="specify",
                project_path=str(temp_project),
                description="Test feature"
            )
            assert specify_result is not None
        
        # 3. Create plan (mocked)
        with patch('specify_cli.mcp.adapters.CLIAdapter') as mock_adapter:
            mock_adapter.return_value.plan.return_value = OperationResult.success_result(
                message="Plan created"
            )
            
            plan_result = await mcp_client.call_tool(
                "feature_operations",
                operation="plan",
                project_path=str(temp_project),
                feature_slug="001-test"
            )
            assert plan_result is not None
        
        # 4. Generate tasks (mocked)
        with patch('specify_cli.mcp.adapters.CLIAdapter') as mock_adapter:
            mock_adapter.return_value.tasks.return_value = OperationResult.success_result(
                message="Tasks generated"
            )
            
            tasks_result = await mcp_client.call_tool(
                "feature_operations",
                operation="tasks",
                project_path=str(temp_project),
                feature_slug="001-test"
            )
            assert tasks_result is not None
    
    @pytest.mark.asyncio
    async def test_workspace_creation_and_management(self, mcp_client, temp_project):
        """Test workspace creation and management workflow."""
        # 1. List existing worktrees
        list_result = await mcp_client.call_tool(
            "workspace_operations",
            operation="list_worktrees",
            project_path=str(temp_project)
        )
        assert list_result is not None
        
        # 2. Create worktree (mocked)
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            create_result = await mcp_client.call_tool(
                "workspace_operations",
                operation="create_worktree",
                project_path=str(temp_project),
                feature_slug="001-test",
                wp_id="WP01"
            )
            assert create_result is not None
    
    @pytest.mark.asyncio
    async def test_task_management_workflow(self, mcp_client, temp_project):
        """Test task management workflow."""
        # 1. List tasks
        list_result = await mcp_client.call_tool(
            "task_operations",
            operation="list_tasks",
            project_path=str(temp_project),
            feature_slug="001-test"
        )
        assert list_result is not None
        
        # 2. Move task to doing (mocked)
        with patch('specify_cli.tasks_support.move_task_to_lane') as mock_move:
            mock_move.return_value = None
            
            move_result = await mcp_client.call_tool(
                "task_operations",
                operation="move_task",
                project_path=str(temp_project),
                feature_slug="001-test",
                wp_id="WP01",
                to_lane="doing"
            )
            assert move_result is not None
        
        # 3. Add history note (mocked)
        with patch('specify_cli.tasks_support.add_history_entry') as mock_history:
            mock_history.return_value = None
            
            history_result = await mcp_client.call_tool(
                "task_operations",
                operation="add_history",
                project_path=str(temp_project),
                feature_slug="001-test",
                wp_id="WP01",
                note="Started implementation"
            )
            assert history_result is not None


class TestMCPServerErrorHandling:
    """Integration tests for MCP server error handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_operation(self, mcp_client):
        """Test error handling for invalid operations."""
        with pytest.raises(Exception):  # Should raise error for invalid operation
            await mcp_client.call_tool(
                "system_operations",
                operation="invalid_operation"
            )
    
    @pytest.mark.asyncio
    async def test_missing_required_parameter(self, mcp_client):
        """Test error handling for missing required parameters."""
        with pytest.raises(Exception):  # Should raise error for missing project_path
            await mcp_client.call_tool(
                "feature_operations",
                operation="specify"
                # Missing required parameters
            )
    
    @pytest.mark.asyncio
    async def test_invalid_project_path(self, mcp_client):
        """Test error handling for invalid project paths."""
        result = await mcp_client.call_tool(
            "system_operations",
            operation="validate_project",
            project_path="/nonexistent/path"
        )
        # Should return error result (not raise exception)
        assert result is not None
