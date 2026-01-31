"""
Tests for system operations MCP tools.

Covers health checks, project validation, mission listing, and server
configuration operations.
"""

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.mcp.tools.system_tools import (
    SYSTEM_OPERATIONS_SCHEMA,
    health_check_operation,
    list_missions_operation,
    server_config_operation,
    system_operations_handler,
    validate_project_operation,
)


class TestHealthCheck:
    """Tests for health_check operation."""
    
    def test_health_check_without_server_instance(self):
        """Health check returns basic status when no server instance provided."""
        result = health_check_operation()
        
        assert result.success is True
        assert result.message == "Server is healthy"
        assert result.data is not None
        assert result.data["status"] == "healthy"
        assert "uptime_seconds" in result.data
        assert result.data["active_projects"] == 0
        assert "timestamp" in result.data
    
    def test_health_check_with_server_instance(self):
        """Health check includes active projects count from server instance."""
        mock_server = MagicMock()
        mock_server.active_projects = {"project1": {}, "project2": {}}
        
        result = health_check_operation(mock_server)
        
        assert result.success is True
        assert result.data["active_projects"] == 2
    
    def test_health_check_uptime_increases(self):
        """Health check uptime increases over time."""
        result1 = health_check_operation()
        time.sleep(0.1)
        result2 = health_check_operation()
        
        assert result2.data["uptime_seconds"] >= result1.data["uptime_seconds"]


class TestValidateProject:
    """Tests for validate_project operation."""
    
    def test_validate_nonexistent_path(self):
        """Validation fails for nonexistent project path."""
        result = validate_project_operation("/nonexistent/path")
        
        assert result.success is False
        assert "does not exist" in result.message
        assert result.errors is not None
        assert len(result.errors) > 0
    
    def test_validate_missing_kittify_directory(self, tmp_path):
        """Validation fails when .kittify/ directory missing."""
        result = validate_project_operation(str(tmp_path))
        
        assert result.success is False
        assert "missing .kittify/ directory" in result.message.lower()
        assert any("Missing .kittify/ directory" in err for err in result.errors)
    
    def test_validate_valid_minimal_project(self, tmp_path):
        """Validation succeeds for minimal valid project."""
        # Create .kittify/ directory
        kittify_dir = tmp_path / ".kittify"
        kittify_dir.mkdir()
        
        result = validate_project_operation(str(tmp_path))
        
        assert result.success is True
        assert result.message == "Project structure is valid"
        assert result.data["is_valid"] is True
        assert result.data["checks"]["kittify_directory"] is True
    
    def test_validate_project_with_all_components(self, tmp_path):
        """Validation detects all optional components when present."""
        # Create full project structure
        kittify_dir = tmp_path / ".kittify"
        kittify_dir.mkdir()
        
        (kittify_dir / "config.yaml").write_text("agents:\n  available: [claude]\n")
        (tmp_path / "kitty-specs").mkdir()
        (kittify_dir / "workspaces").mkdir()
        
        result = validate_project_operation(str(tmp_path))
        
        assert result.success is True
        assert result.data["checks"]["config_file"] is True
        assert result.data["checks"]["specs_directory"] is True
        assert result.data["checks"]["workspace_context_directory"] is True
    
    def test_validate_project_warnings_for_missing_optional(self, tmp_path):
        """Validation includes warnings for missing optional components."""
        # Create minimal valid project (only .kittify/)
        kittify_dir = tmp_path / ".kittify"
        kittify_dir.mkdir()
        
        result = validate_project_operation(str(tmp_path))
        
        assert result.success is True
        assert "warnings" in result.data
        assert any("config.yaml not found" in w for w in result.data["warnings"])
        assert any("kitty-specs/ directory not found" in w for w in result.data["warnings"])


class TestListMissions:
    """Tests for list_missions operation."""
    
    def test_list_missions_returns_available_missions(self):
        """List missions returns available missions from registry."""
        result = list_missions_operation()
        
        assert result.success is True
        assert "missions" in result.data
        assert isinstance(result.data["missions"], list)
        # Should have at least software-dev mission
        assert len(result.data["missions"]) > 0
    
    def test_list_missions_includes_mission_details(self):
        """List missions includes name, display_name, and description."""
        result = list_missions_operation()
        
        missions = result.data["missions"]
        if missions:
            mission = missions[0]
            assert "name" in mission
            # Either has mission details OR an error field
            assert "display_name" in mission or "error" in mission


class TestServerConfig:
    """Tests for server_config operation."""
    
    def test_server_config_without_instance(self):
        """Server config returns defaults when no instance provided."""
        result = server_config_operation()
        
        assert result.success is True
        assert result.message == "Server configuration retrieved"
        assert result.data["config"]["host"] == "127.0.0.1"
        assert result.data["config"]["port"] == 8000
        assert result.data["config"]["transport"] == "stdio"
        assert result.data["config"]["auth_enabled"] is False
    
    def test_server_config_with_instance(self):
        """Server config returns actual server settings."""
        mock_server = MagicMock()
        mock_server.host = "0.0.0.0"
        mock_server.port = 9000
        mock_server.transport = "sse"
        mock_server.auth_enabled = True
        mock_server.api_key = "secret_key_12345"
        
        result = server_config_operation(mock_server)
        
        assert result.success is True
        assert result.data["config"]["host"] == "0.0.0.0"
        assert result.data["config"]["port"] == 9000
        assert result.data["config"]["transport"] == "sse"
        assert result.data["config"]["auth_enabled"] is True
    
    def test_server_config_redacts_api_key(self):
        """Server config redacts API key for security."""
        mock_server = MagicMock()
        mock_server.api_key = "secret_key_12345"
        
        result = server_config_operation(mock_server)
        
        assert result.data["config"]["api_key"] == "***REDACTED***"
        assert "secret_key_12345" not in str(result.data)


class TestSystemOperationsHandler:
    """Tests for system_operations_handler routing."""
    
    def test_handler_routes_health_check(self):
        """Handler routes health_check to correct operation."""
        result_dict = system_operations_handler(operation="health_check")
        
        assert result_dict["success"] is True
        assert result_dict["message"] == "Server is healthy"
    
    def test_handler_routes_validate_project(self, tmp_path):
        """Handler routes validate_project to correct operation."""
        kittify_dir = tmp_path / ".kittify"
        kittify_dir.mkdir()
        
        result_dict = system_operations_handler(
            operation="validate_project",
            project_path=str(tmp_path)
        )
        
        assert result_dict["success"] is True
    
    def test_handler_validate_project_requires_path(self):
        """Handler fails validate_project when project_path missing."""
        result_dict = system_operations_handler(operation="validate_project")
        
        assert result_dict["success"] is False
        assert "requires project_path" in result_dict["message"]
    
    def test_handler_routes_list_missions(self):
        """Handler routes list_missions to correct operation."""
        result_dict = system_operations_handler(operation="list_missions")
        
        assert result_dict["success"] is True
        assert "missions" in result_dict["data"]
    
    def test_handler_routes_server_config(self):
        """Handler routes server_config to correct operation."""
        result_dict = system_operations_handler(operation="server_config")
        
        assert result_dict["success"] is True
        assert "config" in result_dict["data"]
    
    def test_handler_rejects_unknown_operation(self):
        """Handler returns error for unknown operations."""
        result_dict = system_operations_handler(operation="unknown_op")
        
        assert result_dict["success"] is False
        assert "Unknown system operation" in result_dict["message"]
        assert result_dict["errors"] is not None


class TestJSONSchema:
    """Tests for SYSTEM_OPERATIONS_SCHEMA."""
    
    def test_schema_has_required_fields(self):
        """Schema defines required operation field."""
        assert "properties" in SYSTEM_OPERATIONS_SCHEMA
        assert "operation" in SYSTEM_OPERATIONS_SCHEMA["properties"]
        assert "required" in SYSTEM_OPERATIONS_SCHEMA
        assert "operation" in SYSTEM_OPERATIONS_SCHEMA["required"]
    
    def test_schema_operation_enum(self):
        """Schema restricts operation to valid values."""
        operation_prop = SYSTEM_OPERATIONS_SCHEMA["properties"]["operation"]
        assert "enum" in operation_prop
        
        expected_operations = {
            "health_check",
            "validate_project",
            "list_missions",
            "server_config",
        }
        assert set(operation_prop["enum"]) == expected_operations
    
    def test_schema_has_project_path_optional(self):
        """Schema defines optional project_path parameter."""
        assert "project_path" in SYSTEM_OPERATIONS_SCHEMA["properties"]
        assert "project_path" not in SYSTEM_OPERATIONS_SCHEMA["required"]
