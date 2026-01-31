"""
Feature operations MCP tools.

Provides conversational access to feature workflow operations:
- specify: Create feature specification with discovery interview
- plan: Generate technical plan
- tasks: Create work package breakdown
- implement: Create worktree for work package
- review: Review work package implementation
- accept: Merge completed feature to main branch
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from specify_cli.mcp.adapters import CLIAdapter, OperationResult
from specify_cli.mcp.session.context import ProjectContext

logger = logging.getLogger(__name__)


class FeatureOperation(str, Enum):
    """Supported feature operations."""
    SPECIFY = "specify"
    PLAN = "plan"
    TASKS = "tasks"
    IMPLEMENT = "implement"
    REVIEW = "review"
    ACCEPT = "accept"


# JSON Schema for feature_operations tool parameters
FEATURE_OPERATIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "project_path": {
            "type": "string",
            "description": "Absolute path to the spec-kitty project root"
        },
        "operation": {
            "type": "string",
            "enum": ["specify", "plan", "tasks", "implement", "review", "accept"],
            "description": "Feature workflow operation to perform"
        },
        "feature_slug": {
            "type": "string",
            "description": "Feature slug (e.g., '099-mcp-server'). Required for all operations except specify."
        },
        "arguments": {
            "type": "object",
            "description": "Operation-specific arguments",
            "properties": {
                # Specify operation
                "description": {"type": "string", "description": "Feature description (for specify)"},
                "slug": {"type": "string", "description": "Feature slug (for specify)"},
                
                # Implement operation
                "wp_id": {"type": "string", "description": "Work package ID (e.g., 'WP01')"},
                "base_wp": {"type": "string", "description": "Base work package to branch from (optional)"},
                
                # Review operation
                "reviewer": {"type": "string", "description": "Reviewer name"},
                "status": {"type": "string", "enum": ["approved", "changes_requested"], "description": "Review decision"},
                "comments": {"type": "string", "description": "Review comments"},
                
                # Accept operation
                "merge_strategy": {"type": "string", "enum": ["merge", "squash", "rebase"], "description": "Merge strategy (default: merge)"}
            },
            "additionalProperties": True
        }
    },
    "required": ["project_path", "operation"]
}


def feature_operations_handler(
    project_path: str,
    operation: str,
    feature_slug: Optional[str] = None,
    arguments: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main handler for feature operations.
    
    Routes to appropriate operation handler based on operation parameter.
    Validates project context and parameters before delegating to CLIAdapter.
    
    Args:
        project_path: Absolute path to project root
        operation: Operation to perform (specify, plan, tasks, implement, review, accept)
        feature_slug: Feature slug (required for non-specify operations)
        arguments: Operation-specific arguments
    
    Returns:
        Serialized OperationResult as dictionary
    """
    try:
        # Validate operation
        try:
            op_enum = FeatureOperation(operation)
        except ValueError:
            return OperationResult.error_result(
                message=f"Invalid operation: {operation}",
                errors=[f"Must be one of: {', '.join(op.value for op in FeatureOperation)}"]
            ).to_dict()
        
        # Create project context
        try:
            ctx = ProjectContext.from_path(Path(project_path))
        except Exception as e:
            return OperationResult.error_result(
                message=f"Invalid project path: {project_path}",
                errors=[str(e)]
            ).to_dict()
        
        # Create CLI adapter
        adapter = CLIAdapter(ctx)
        args = arguments or {}
        
        # Route to operation handler
        if op_enum == FeatureOperation.SPECIFY:
            result = _handle_specify(adapter, args)
        elif op_enum == FeatureOperation.PLAN:
            result = _handle_plan(adapter, feature_slug, args)
        elif op_enum == FeatureOperation.TASKS:
            result = _handle_tasks(adapter, feature_slug, args)
        elif op_enum == FeatureOperation.IMPLEMENT:
            result = _handle_implement(adapter, feature_slug, args)
        elif op_enum == FeatureOperation.REVIEW:
            result = _handle_review(adapter, feature_slug, args)
        elif op_enum == FeatureOperation.ACCEPT:
            result = _handle_accept(adapter, feature_slug, args)
        else:
            result = OperationResult.error_result(
                message=f"Operation {operation} not implemented",
                errors=["Handler not found"]
            )
        
        return result.to_dict()
        
    except Exception as e:
        logger.exception("Unexpected error in feature_operations_handler")
        return OperationResult.error_result(
            message=f"Unexpected error: {str(e)}",
            errors=[str(e), "See server logs for details"]
        ).to_dict()


def _handle_specify(
    adapter: CLIAdapter,
    args: Dict[str, Any]
) -> OperationResult:
    """
    Handle specify operation - create feature specification.
    
    NOTE: Full discovery interview logic is complex and handled by
    existing CLI commands. This implementation creates a basic feature
    structure. For production, integrate with ConversationState (WP02).
    
    Args:
        adapter: CLIAdapter instance
        args: Must contain 'slug' and 'description'
    
    Returns:
        OperationResult with feature creation status
    """
    slug = args.get("slug")
    description = args.get("description", "")
    
    if not slug:
        return OperationResult.error_result(
            message="Missing required argument: slug",
            errors=["'slug' is required for specify operation"]
        )
    
    # Delegate to CLIAdapter
    return adapter.create_feature(slug=slug, description=description)


def _handle_plan(
    adapter: CLIAdapter,
    feature_slug: Optional[str],
    args: Dict[str, Any]
) -> OperationResult:
    """
    Handle plan operation - generate technical plan.
    
    Args:
        adapter: CLIAdapter instance
        feature_slug: Feature slug (required)
        args: Additional arguments (unused currently)
    
    Returns:
        OperationResult with plan creation status
    """
    if not feature_slug:
        return OperationResult.error_result(
            message="Missing required parameter: feature_slug",
            errors=["feature_slug is required for plan operation"]
        )
    
    return adapter.setup_plan(feature_slug=feature_slug)


def _handle_tasks(
    adapter: CLIAdapter,
    feature_slug: Optional[str],
    args: Dict[str, Any]
) -> OperationResult:
    """
    Handle tasks operation - create work package breakdown.
    
    Args:
        adapter: CLIAdapter instance
        feature_slug: Feature slug (required)
        args: Additional arguments (unused currently)
    
    Returns:
        OperationResult with tasks creation status
    """
    if not feature_slug:
        return OperationResult.error_result(
            message="Missing required parameter: feature_slug",
            errors=["feature_slug is required for tasks operation"]
        )
    
    return adapter.create_tasks(feature_slug=feature_slug)


def _handle_implement(
    adapter: CLIAdapter,
    feature_slug: Optional[str],
    args: Dict[str, Any]
) -> OperationResult:
    """
    Handle implement operation - create worktree for work package.
    
    Args:
        adapter: CLIAdapter instance
        feature_slug: Feature slug (required)
        args: Must contain 'wp_id', optional 'base_wp'
    
    Returns:
        OperationResult with worktree creation status
    """
    if not feature_slug:
        return OperationResult.error_result(
            message="Missing required parameter: feature_slug",
            errors=["feature_slug is required for implement operation"]
        )
    
    wp_id = args.get("wp_id")
    if not wp_id:
        return OperationResult.error_result(
            message="Missing required argument: wp_id",
            errors=["'wp_id' is required for implement operation"]
        )
    
    base_wp = args.get("base_wp")
    
    return adapter.create_worktree(
        feature_slug=feature_slug,
        wp_id=wp_id,
        base_wp=base_wp
    )


def _handle_review(
    adapter: CLIAdapter,
    feature_slug: Optional[str],
    args: Dict[str, Any]
) -> OperationResult:
    """
    Handle review operation - review work package implementation.
    
    NOTE: Full review logic involves validation, testing, and feedback.
    This is a placeholder implementation. Full logic should be extracted
    to src/specify_cli/core/review.py.
    
    Args:
        adapter: CLIAdapter instance
        feature_slug: Feature slug (required)
        args: Must contain 'wp_id', 'reviewer', 'status', optional 'comments'
    
    Returns:
        OperationResult with review status
    """
    if not feature_slug:
        return OperationResult.error_result(
            message="Missing required parameter: feature_slug",
            errors=["feature_slug is required for review operation"]
        )
    
    wp_id = args.get("wp_id")
    reviewer = args.get("reviewer")
    status = args.get("status")
    comments = args.get("comments", "")
    
    if not wp_id:
        return OperationResult.error_result(
            message="Missing required argument: wp_id",
            errors=["'wp_id' is required for review operation"]
        )
    
    if not reviewer:
        return OperationResult.error_result(
            message="Missing required argument: reviewer",
            errors=["'reviewer' is required for review operation"]
        )
    
    if not status:
        return OperationResult.error_result(
            message="Missing required argument: status",
            errors=["'status' is required (approved or changes_requested)"]
        )
    
    # For now, add history entry with review
    note = f"Review by {reviewer}: {status}"
    if comments:
        note += f" - {comments}"
    
    result = adapter.add_history(
        feature_slug=feature_slug,
        task_id=wp_id,
        note=note
    )
    
    if result.success:
        result.message = f"Review recorded for {wp_id}: {status}"
        result.warnings.append("Full review workflow not yet implemented - recorded as history entry")
    
    return result


def _handle_accept(
    adapter: CLIAdapter,
    feature_slug: Optional[str],
    args: Dict[str, Any]
) -> OperationResult:
    """
    Handle accept operation - merge completed feature to main branch.
    
    NOTE: Full merge logic is complex (preflight checks, conflict resolution).
    This is a placeholder. Full logic in src/specify_cli/merge/ should be
    wrapped here.
    
    Args:
        adapter: CLIAdapter instance
        feature_slug: Feature slug (required)
        args: Optional 'merge_strategy' (merge/squash/rebase)
    
    Returns:
        OperationResult with merge status
    """
    if not feature_slug:
        return OperationResult.error_result(
            message="Missing required parameter: feature_slug",
            errors=["feature_slug is required for accept operation"]
        )
    
    merge_strategy = args.get("merge_strategy", "merge")
    
    # Placeholder implementation
    result = OperationResult.success_result(
        message=f"Accept operation initiated for {feature_slug}",
        data={
            "feature_slug": feature_slug,
            "merge_strategy": merge_strategy,
            "status": "not_implemented"
        }
    )
    result.warnings = [
        "Full accept/merge workflow not yet implemented",
        f"For now, run: spec-kitty merge --feature {feature_slug}"
    ]
    return result


# Export for MCP tool registration
__all__ = [
    "feature_operations_handler",
    "FEATURE_OPERATIONS_SCHEMA",
    "FeatureOperation"
]
