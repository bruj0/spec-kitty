"""
MCP (Model Context Protocol) server implementation for Spec Kitty.

Provides conversational AI interface to Spec Kitty workflows through
MCP tools, eliminating the need for users to learn slash commands.

Architecture:
- server.py: FastMCP server initialization and configuration
- config.py: Configuration and PID file management
- tools/: Domain-grouped MCP tool definitions
- adapters/: CLI adapter layer (wraps existing CLI modules)
- session/: Conversation state and project context management
- auth/: Optional API key authentication
"""

__all__ = ["MCPServer", "MCPConfig", "PIDFileManager"]

from .config import MCPConfig, PIDFileManager
from .server import MCPServer
