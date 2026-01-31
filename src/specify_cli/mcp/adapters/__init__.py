"""
CLI adapter layer for MCP tool integration.

Provides a consistent interface for MCP tools to invoke existing CLI
functionality without duplicating business logic. Wraps CLI modules
with standardized error handling and result formatting.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class OperationResult:
    """Standardized result format for MCP tool operations."""
    
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    artifacts: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for MCP response."""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "artifacts": [str(p) for p in self.artifacts],
            "errors": self.errors,
            "warnings": self.warnings
        }
    
    @classmethod
    def success_result(
        cls,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        artifacts: Optional[List[Path]] = None
    ) -> "OperationResult":
        """Create success result."""
        return cls(
            success=True,
            message=message,
            data=data,
            artifacts=artifacts or []
        )
    
    @classmethod
    def error_result(
        cls,
        message: str,
        errors: Optional[List[str]] = None
    ) -> "OperationResult":
        """Create error result."""
        return cls(
            success=False,
            message=message,
            errors=errors or [message]
        )


from .cli_adapter import CLIAdapter

__all__ = ["OperationResult", "CLIAdapter"]
