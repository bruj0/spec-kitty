"""
MCP tool handlers for Spec Kitty operations.

Domain-grouped tools that translate MCP requests into CLI operations.
Each tool handles parameter validation, routing to CLI adapters, and
response serialization.
"""

from .workspace_tools import workspace_operations

__all__ = ["workspace_operations"]
