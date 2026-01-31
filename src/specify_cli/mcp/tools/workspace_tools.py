"""
Workspace operations MCP tools.

Handles git worktree management operations (create, list, merge).
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastmcp import Context

from specify_cli.mcp.adapters import OperationResult
from specify_cli.mcp.adapters.cli_adapter import CLIAdapter
from specify_cli.mcp.session.context import ProjectContext

logger = logging.getLogger(__name__)


def workspace_operations(
    project_path: str,
    operation: str,
    work_package_id: Optional[str] = None,
    base_wp: Optional[str] = None,
    feature_slug: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Handle workspace operations for git worktrees.
    
    Operations:
    - create_worktree: Create new worktree for work package (requires work_package_id)
    - list_worktrees: List all active worktrees
    - merge: Merge worktrees back to main branch (requires feature_slug)
    
    Args:
        project_path: Absolute path to Spec Kitty project root
        operation: Operation to perform (create_worktree, list_worktrees, merge)
        work_package_id: WP ID for create_worktree (e.g., "WP01")
        base_wp: Base WP for dependency branching (optional, for create_worktree)
        feature_slug: Feature identifier for merge (e.g., "099-my-feature")
        ctx: FastMCP context (optional, for server integration)
    
    Returns:
        Serialized OperationResult as dict
    
    Raises:
        ValueError: If required parameters missing for operation
    """
    try:
        # Validate project path
        project_root = Path(project_path)
        if not project_root.exists():
            return OperationResult.error_result(
                message=f"Project path does not exist: {project_path}",
                errors=[f"Directory not found: {project_path}"]
            ).to_dict()
        
        # Create project context
        try:
            project_context = ProjectContext.from_path(project_root)
        except Exception as e:
            return OperationResult.error_result(
                message=f"Invalid project path: {str(e)}",
                errors=[
                    str(e),
                    "Ensure .kittify/ directory exists in project root"
                ]
            ).to_dict()
        
        # Create CLI adapter
        adapter = CLIAdapter(project_context)
        
        # Route to operation handler
        if operation == "create_worktree":
            result = _handle_create_worktree(
                adapter,
                work_package_id,
                base_wp,
                feature_slug,
                project_root
            )
        elif operation == "list_worktrees":
            result = _handle_list_worktrees(adapter)
        elif operation == "merge":
            result = _handle_merge(adapter, feature_slug)
        else:
            result = OperationResult.error_result(
                message=f"Unknown operation: {operation}",
                errors=[
                    f"Invalid operation: {operation}",
                    "Valid operations: create_worktree, list_worktrees, merge"
                ]
            )
        
        return result.to_dict()
    
    except Exception as e:
        logger.exception("Workspace operations handler error")
        return OperationResult.error_result(
            message=f"Workspace operation failed: {str(e)}",
            errors=[str(e), "See logs for full traceback"]
        ).to_dict()


def _handle_create_worktree(
    adapter: CLIAdapter,
    work_package_id: Optional[str],
    base_wp: Optional[str],
    feature_slug: Optional[str],
    project_root: Path
) -> OperationResult:
    """Handle create_worktree operation."""
    # Validate required parameters
    if not work_package_id:
        return OperationResult.error_result(
            message="Missing required parameter: work_package_id",
            errors=["work_package_id is required for create_worktree operation"]
        )
    
    # Detect feature slug from context if not provided
    if not feature_slug:
        # Try to detect from latest incomplete feature
        from specify_cli.core.feature_detection import detect_feature_slug, FeatureDetectionError
        try:
            feature_slug = detect_feature_slug(project_root)
        except FeatureDetectionError:
            return OperationResult.error_result(
                message="Could not detect feature context",
                errors=[
                    "feature_slug not provided and auto-detection failed",
                    "Provide feature_slug explicitly or ensure active feature exists"
                ]
            )
    
    # Call CLI adapter
    return adapter.create_worktree(
        feature_slug=feature_slug,
        wp_id=work_package_id,
        base_wp=base_wp
    )


def _handle_list_worktrees(adapter: CLIAdapter) -> OperationResult:
    """Handle list_worktrees operation."""
    return adapter.list_worktrees()


def _handle_merge(
    adapter: CLIAdapter,
    feature_slug: Optional[str]
) -> OperationResult:
    """Handle merge operation."""
    # Validate required parameters
    if not feature_slug:
        return OperationResult.error_result(
            message="Missing required parameter: feature_slug",
            errors=["feature_slug is required for merge operation"]
        )
    
    # Delegate to adapter (which wraps existing merge workflow)
    try:
        from specify_cli.merge.executor import merge_feature
        
        result = merge_feature(
            feature_slug=feature_slug,
            target_branch="main",
            strategy="merge",
            dry_run=False
        )
        
        # Convert merge result to OperationResult
        if result["success"]:
            return OperationResult.success_result(
                message=result["message"],
                data=result.get("data", {})
            )
        else:
            return OperationResult.error_result(
                message=result["message"],
                errors=result.get("errors", [])
            )
    
    except ImportError:
        return OperationResult.error_result(
            message="Merge workflow not available",
            errors=[
                "Merge functionality requires complete merge module",
                "This feature may not be implemented yet"
            ],
            warnings=["Placeholder: full merge implementation pending"]
        )
    except Exception as e:
        return OperationResult.error_result(
            message=f"Merge operation failed: {str(e)}",
            errors=[str(e)]
        )
