"""MCP tools for task management operations.

This module provides MCP tools for task operations:
- list_tasks: List all tasks for a feature, optionally filtered by lane
- move_task: Move task between lanes with locking
- add_history: Add activity log entry to task
- query_status: Get task status including lane, dependencies, and completion
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

from specify_cli.mcp.adapters import OperationResult, CLIAdapter
from specify_cli.mcp.session.context import ProjectContext
from specify_cli.mcp.session.locking import ResourceLock, LockTimeout

logger = logging.getLogger(__name__)

# JSON Schema for task_operations parameters (T038)
TASK_OPERATIONS_SCHEMA = {
    "type": "object",
    "required": ["project_path", "operation"],
    "properties": {
        "project_path": {
            "type": "string",
            "description": "Absolute path to the Spec Kitty project root"
        },
        "operation": {
            "type": "string",
            "enum": ["list_tasks", "move_task", "add_history", "query_status"],
            "description": "Task operation to perform"
        },
        "feature_slug": {
            "type": "string",
            "description": "Feature slug (e.g., '099-mcp-server-for-conversational-spec-kitty-workflow')"
        },
        "task_id": {
            "type": "string",
            "description": "Work package ID (e.g., 'WP01'). Required for move_task, add_history, query_status"
        },
        "lane": {
            "type": "string",
            "enum": ["planned", "doing", "for_review", "done"],
            "description": "Target lane for move_task operation, or filter lane for list_tasks"
        },
        "note": {
            "type": "string",
            "description": "Note to add for add_history or move_task operations"
        }
    }
}


def _get_project_context(project_path: str) -> ProjectContext:
    """Create ProjectContext with validation.
    
    Args:
        project_path: Path to project root
        
    Returns:
        Validated ProjectContext
        
    Raises:
        ValueError: If project_path is invalid
    """
    try:
        path = Path(project_path).resolve()
        return ProjectContext(project_path=path)
    except Exception as e:
        raise ValueError(f"Invalid project path: {e}")


def _query_task_status(
    cli_adapter: CLIAdapter,
    feature_slug: str,
    task_id: str
) -> OperationResult:
    """Query task status including lane, dependencies, and completion.
    
    Args:
        cli_adapter: CLI adapter instance
        feature_slug: Feature slug
        task_id: Work package ID
        
    Returns:
        OperationResult with task status data
    """
    try:
        from specify_cli.tasks_support import split_frontmatter, extract_scalar
        
        feature_dir = cli_adapter.project_context.get_feature_dir(feature_slug)
        tasks_dir = feature_dir / "tasks"
        
        # Find task file
        task_file = None
        for f in tasks_dir.glob("WP*.md"):
            if task_id in f.stem:
                task_file = f
                break
        
        if not task_file:
            return OperationResult.error_result(
                message=f"Task {task_id} not found",
                errors=[f"No file matching {task_id} in {tasks_dir}"]
            )
        
        # Read and parse frontmatter
        content = task_file.read_text(encoding="utf-8-sig")
        frontmatter, _, _ = split_frontmatter(content)
        
        # Extract status fields
        lane = extract_scalar(frontmatter, "lane") or "planned"
        title = extract_scalar(frontmatter, "title") or ""
        dependencies = frontmatter.get("dependencies", [])
        subtasks = frontmatter.get("subtasks", [])
        assignee = extract_scalar(frontmatter, "assignee") or ""
        agent = extract_scalar(frontmatter, "agent") or ""
        review_status = extract_scalar(frontmatter, "review_status") or ""
        history = frontmatter.get("history", [])
        
        # Calculate completion status
        is_done = lane == "done"
        has_dependencies = len(dependencies) > 0
        
        return OperationResult.success_result(
            message=f"Retrieved status for {task_id}",
            data={
                "task_id": task_id,
                "title": title,
                "lane": lane,
                "dependencies": dependencies,
                "subtasks": subtasks,
                "assignee": assignee,
                "agent": agent,
                "review_status": review_status,
                "is_done": is_done,
                "has_dependencies": has_dependencies,
                "history_count": len(history),
                "path": str(task_file)
            }
        )
    except Exception as e:
        return OperationResult.error_result(
            message=f"Failed to query task status: {str(e)}",
            errors=[str(e)]
        )


# Task operations handler (T039)
def task_operations_handler(
    project_path: str,
    operation: str,
    feature_slug: Optional[str] = None,
    task_id: Optional[str] = None,
    lane: Optional[str] = None,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """Route task operations to appropriate handlers.
    
    This is the main entry point for all task operations. It validates
    parameters, creates the necessary adapters, and delegates to the
    appropriate operation handler.
    
    Args:
        project_path: Absolute path to Spec Kitty project root
        operation: Task operation to perform (list_tasks, move_task, add_history, query_status)
        feature_slug: Feature slug (required for all operations)
        task_id: Work package ID (required for move_task, add_history, query_status)
        lane: Target lane (required for move_task) or filter lane (optional for list_tasks)
        note: Note for add_history or move_task operations
        
    Returns:
        Dictionary representation of OperationResult
        
    Raises:
        ValueError: If required parameters are missing
    """
    try:
        # Validate project path and create context
        context = _get_project_context(project_path)
        cli_adapter = CLIAdapter(context)
        
        # Route to operation handler
        if operation == "list_tasks":
            # list_tasks: requires feature_slug, optional lane filter
            if not feature_slug:
                return OperationResult.error_result(
                    message="Missing required parameter: feature_slug",
                    errors=["feature_slug is required for list_tasks operation"]
                ).to_dict()
            
            result = cli_adapter.list_tasks(feature_slug, lane)
            return result.to_dict()
        
        elif operation == "move_task":
            # move_task: requires feature_slug, task_id, lane
            # MUST use locking (WP03)
            if not all([feature_slug, task_id, lane]):
                return OperationResult.error_result(
                    message="Missing required parameters",
                    errors=[
                        "move_task requires: feature_slug, task_id, lane",
                        f"Got: feature_slug={feature_slug}, task_id={task_id}, lane={lane}"
                    ]
                ).to_dict()
            
            # Acquire lock for work package
            lock = ResourceLock.for_work_package(
                lock_dir=context.lock_dir,
                wp_id=task_id,
                timeout_seconds=300  # 5 minutes
            )
            
            try:
                with lock.acquire():
                    # Execute move_task with lock held
                    result = cli_adapter.move_task(
                        feature_slug=feature_slug,
                        task_id=task_id,
                        lane=lane,
                        note=note
                    )
                    return result.to_dict()
            except LockTimeout as e:
                return OperationResult.error_result(
                    message=f"Failed to acquire lock for {task_id}",
                    errors=[str(e)]
                ).to_dict()
        
        elif operation == "add_history":
            # add_history: requires feature_slug, task_id, note
            if not all([feature_slug, task_id, note]):
                return OperationResult.error_result(
                    message="Missing required parameters",
                    errors=[
                        "add_history requires: feature_slug, task_id, note",
                        f"Got: feature_slug={feature_slug}, task_id={task_id}, note={note}"
                    ]
                ).to_dict()
            
            # Acquire lock for work package (history updates frontmatter)
            lock = ResourceLock.for_work_package(
                lock_dir=context.lock_dir,
                wp_id=task_id,
                timeout_seconds=300
            )
            
            try:
                with lock.acquire():
                    result = cli_adapter.add_history(
                        feature_slug=feature_slug,
                        task_id=task_id,
                        note=note
                    )
                    return result.to_dict()
            except LockTimeout as e:
                return OperationResult.error_result(
                    message=f"Failed to acquire lock for {task_id}",
                    errors=[str(e)]
                ).to_dict()
        
        elif operation == "query_status":
            # query_status: requires feature_slug, task_id
            if not all([feature_slug, task_id]):
                return OperationResult.error_result(
                    message="Missing required parameters",
                    errors=[
                        "query_status requires: feature_slug, task_id",
                        f"Got: feature_slug={feature_slug}, task_id={task_id}"
                    ]
                ).to_dict()
            
            result = _query_task_status(cli_adapter, feature_slug, task_id)
            return result.to_dict()
        
        else:
            return OperationResult.error_result(
                message=f"Unknown operation: {operation}",
                errors=[
                    f"Operation '{operation}' is not recognized",
                    "Valid operations: list_tasks, move_task, add_history, query_status"
                ]
            ).to_dict()
    
    except ValueError as e:
        return OperationResult.error_result(
            message="Invalid parameters",
            errors=[str(e)]
        ).to_dict()
    except Exception as e:
        logger.exception(f"Unexpected error in task_operations_handler: {e}")
        return OperationResult.error_result(
            message=f"Internal error: {str(e)}",
            errors=[str(e)]
        ).to_dict()


def register_task_operations_tool(mcp_server):
    """Register task_operations tool with FastMCP server (T044).
    
    This function is called during server initialization to register
    the task_operations tool with the MCP server instance.
    
    Args:
        mcp_server: FastMCP server instance to register tool with
    """
    @mcp_server.tool(
        name="task_operations",
        description="Manage Spec Kitty tasks (list, move, add history, query status)",
        parameters=TASK_OPERATIONS_SCHEMA
    )
    def task_operations(
        project_path: str,
        operation: str,
        feature_slug: Optional[str] = None,
        task_id: Optional[str] = None,
        lane: Optional[str] = None,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """MCP tool wrapper for task operations."""
        return task_operations_handler(
            project_path=project_path,
            operation=operation,
            feature_slug=feature_slug,
            task_id=task_id,
            lane=lane,
            note=note
        )
    
    logger.info("Registered task_operations tool with MCP server")
