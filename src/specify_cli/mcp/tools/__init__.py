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

__all__ = [
    "SYSTEM_OPERATIONS_SCHEMA",
    "system_operations_handler",
]
