"""
MCP tool handlers for Spec Kitty operations.

Domain-grouped tools that translate MCP requests into CLI operations.
Each tool handles parameter validation, routing to CLI adapters, and
response serialization.
"""

from .task_tools import (
    register_task_operations_tool,
    task_operations_handler,
    TASK_OPERATIONS_SCHEMA,
)

__all__ = [
    "register_task_operations_tool",
    "task_operations_handler",
    "TASK_OPERATIONS_SCHEMA",
]
