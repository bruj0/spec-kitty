"""
System operations MCP tools.

Provides health checks, project validation, mission listing, and server
configuration tools for MCP clients.
"""

import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from specify_cli.core.project_state import ProjectPaths


# Server startup timestamp for uptime calculation
_SERVER_START_TIME = time.time()


@dataclass
class OperationResult:
    """
    Standardized result format for system operations.
    
    Attributes:
        success: Whether the operation completed successfully
        message: Human-readable status message
        data: Operation-specific data (structured dict)
        errors: List of error messages if operation failed
    """
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[list[str]] = None


def health_check_operation(server_instance: Optional[Any] = None) -> OperationResult:
    """
    Return server health status and runtime metrics.
    
    Args:
        server_instance: Optional MCPServer instance for active projects count
        
    Returns:
        OperationResult with health status, uptime, and active projects count
    """
    uptime_seconds = int(time.time() - _SERVER_START_TIME)
    active_projects_count = 0
    
    if server_instance and hasattr(server_instance, "active_projects"):
        active_projects_count = len(server_instance.active_projects)
    
    return OperationResult(
        success=True,
        message="Server is healthy",
        data={
            "status": "healthy",
            "uptime_seconds": uptime_seconds,
            "active_projects": active_projects_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def validate_project_operation(project_path: str) -> OperationResult:
    """
    Validate project structure and check for required files.
    
    Args:
        project_path: Absolute path to project root directory
        
    Returns:
        OperationResult with validation results
    """
    try:
        path = Path(project_path).resolve()
        
        if not path.exists():
            return OperationResult(
                success=False,
                message=f"Project path does not exist: {project_path}",
                errors=[f"Directory not found: {project_path}"],
            )
        
        # Check for .kittify/ directory
        kittify_dir = path / ".kittify"
        if not kittify_dir.exists():
            return OperationResult(
                success=False,
                message="Not a valid Spec Kitty project (missing .kittify/ directory)",
                errors=[
                    "Missing .kittify/ directory",
                    f"Run 'spec-kitty init' in {project_path} to initialize",
                ],
            )
        
        # Check for config.yaml
        config_file = kittify_dir / "config.yaml"
        config_exists = config_file.exists()
        
        # Check for kitty-specs/ directory
        specs_dir = path / "kitty-specs"
        specs_exists = specs_dir.exists()
        
        # Use ProjectPaths to get centralized paths
        try:
            project_paths = ProjectPaths.from_project_root(path)
            workspace_context_dir_exists = project_paths.workspace_context_dir.exists()
        except Exception:
            workspace_context_dir_exists = False
        
        validation_results = {
            "project_path": str(path),
            "is_valid": True,
            "checks": {
                "kittify_directory": True,
                "config_file": config_exists,
                "specs_directory": specs_exists,
                "workspace_context_directory": workspace_context_dir_exists,
            },
        }
        
        # Report any missing optional components
        warnings = []
        if not config_exists:
            warnings.append("config.yaml not found (using defaults)")
        if not specs_exists:
            warnings.append("kitty-specs/ directory not found (no features yet)")
        if not workspace_context_dir_exists:
            warnings.append(".kittify/workspaces/ directory not found (no worktrees yet)")
        
        if warnings:
            validation_results["warnings"] = warnings
        
        return OperationResult(
            success=True,
            message="Project structure is valid",
            data=validation_results,
        )
        
    except Exception as e:
        return OperationResult(
            success=False,
            message=f"Project validation failed: {e}",
            errors=[str(e)],
        )


def list_missions_operation() -> OperationResult:
    """
    List available missions from mission configurations.
    
    Returns:
        OperationResult with list of available missions
    """
    try:
        # Import mission utilities
        from specify_cli.mission import discover_missions
        from specify_cli.core.project_state import ProjectPaths
        
        # Get mission root from package
        import specify_cli
        package_root = Path(specify_cli.__file__).parent
        missions_root = package_root / "missions"
        
        if not missions_root.exists():
            return OperationResult(
                success=False,
                message="Missions directory not found",
                errors=["Built-in missions directory not found in package"],
            )
        
        # List mission directories (each subdirectory is a mission)
        missions = []
        for mission_dir in missions_root.iterdir():
            if not mission_dir.is_dir():
                continue
            
            mission_yaml = mission_dir / "mission.yaml"
            if not mission_yaml.exists():
                continue
            
            try:
                import yaml
                with open(mission_yaml, "r") as f:
                    mission_data = yaml.safe_load(f)
                
                missions.append({
                    "name": mission_dir.name,
                    "display_name": mission_data.get("name", mission_dir.name),
                    "description": mission_data.get("description", ""),
                    "domain": mission_data.get("domain", ""),
                    "version": mission_data.get("version", ""),
                })
            except Exception as e:
                # Skip missions that fail to load
                missions.append({
                    "name": mission_dir.name,
                    "error": f"Failed to load mission: {e}",
                })
        
        return OperationResult(
            success=True,
            message=f"Found {len(missions)} available missions",
            data={"missions": missions},
        )
        
    except Exception as e:
        return OperationResult(
            success=False,
            message=f"Failed to list missions: {e}",
            errors=[str(e)],
        )


def server_config_operation(server_instance: Optional[Any] = None) -> OperationResult:
    """
    Return server configuration with sensitive values redacted.
    
    Args:
        server_instance: Optional MCPServer instance for configuration details
        
    Returns:
        OperationResult with server configuration
    """
    try:
        config = {
            "host": "127.0.0.1",
            "port": 8000,
            "transport": "stdio",
            "auth_enabled": False,
        }
        
        if server_instance:
            config["host"] = getattr(server_instance, "host", "127.0.0.1")
            config["port"] = getattr(server_instance, "port", 8000)
            config["transport"] = getattr(server_instance, "transport", "stdio")
            config["auth_enabled"] = getattr(server_instance, "auth_enabled", False)
            
            # Redact API key if present
            if hasattr(server_instance, "api_key") and server_instance.api_key:
                config["api_key"] = "***REDACTED***"
        
        return OperationResult(
            success=True,
            message="Server configuration retrieved",
            data={"config": config},
        )
        
    except Exception as e:
        return OperationResult(
            success=False,
            message=f"Failed to retrieve server configuration: {e}",
            errors=[str(e)],
        )


def system_operations_handler(
    operation: Literal["health_check", "validate_project", "list_missions", "server_config"],
    project_path: Optional[str] = None,
    server_instance: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Route system operations to appropriate handlers.
    
    Args:
        operation: System operation to perform
        project_path: Project path (required for validate_project)
        server_instance: MCPServer instance (optional, for health/config)
        
    Returns:
        Serialized OperationResult as dict
    """
    if operation == "health_check":
        result = health_check_operation(server_instance)
    
    elif operation == "validate_project":
        if not project_path:
            result = OperationResult(
                success=False,
                message="validate_project requires project_path parameter",
                errors=["Missing required parameter: project_path"],
            )
        else:
            result = validate_project_operation(project_path)
    
    elif operation == "list_missions":
        result = list_missions_operation()
    
    elif operation == "server_config":
        result = server_config_operation(server_instance)
    
    else:
        result = OperationResult(
            success=False,
            message=f"Unknown system operation: {operation}",
            errors=[
                f"Invalid operation: {operation}",
                "Valid operations: health_check, validate_project, list_missions, server_config",
            ],
        )
    
    return asdict(result)


# JSON Schema for system_operations tool
SYSTEM_OPERATIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["health_check", "validate_project", "list_missions", "server_config"],
            "description": "System operation to perform",
        },
        "project_path": {
            "type": "string",
            "description": "Absolute path to project root (required for validate_project)",
        },
    },
    "required": ["operation"],
}
