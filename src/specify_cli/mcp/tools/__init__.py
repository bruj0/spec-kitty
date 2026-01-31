"""
MCP tool handlers for Spec Kitty operations.

Domain-grouped tools that translate MCP requests into CLI operations.
Each tool handles parameter validation, routing to CLI adapters, and
response serialization.
"""

from .system_tools import (
    SYSTEM_OPERATIONS_SCHEMA,
    system_operations_handler,
)
from .feature_tools import (
    feature_operations_handler,
    FEATURE_OPERATIONS_SCHEMA,
    FeatureOperation
)
from .task_tools import (
    register_task_operations_tool,
    task_operations_handler,
    TASK_OPERATIONS_SCHEMA,
)
from .workspace_tools import workspace_operations

__all__ = [
    "SYSTEM_OPERATIONS_SCHEMA",
    "system_operations_handler",
    "feature_operations_handler",
    "FEATURE_OPERATIONS_SCHEMA",
    "FeatureOperation",
    "register_task_operations_tool",
    "task_operations_handler",
    "TASK_OPERATIONS_SCHEMA",
    "workspace_operations",
]
