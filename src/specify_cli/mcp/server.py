"""
FastMCP server initialization and configuration.

Main server class that handles MCP protocol communication, configuration,
and tool registration. Supports both stdio and SSE transports.
"""

import os
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Literal, Optional

from fastmcp import FastMCP


@dataclass
class MCPServer:
    """
    Main MCP server instance for Spec Kitty conversational interface.
    
    Manages MCP protocol communication, multiple project contexts, and
    routes tool invocations to the appropriate CLI adapters.
    
    Attributes:
        host: Server bind address (default: "127.0.0.1")
        port: Server port (default: 8000, SSE only)
        transport: Transport mode ("stdio" or "sse")
        auth_enabled: Whether API key authentication is required
        api_key: Server API key (if auth_enabled=True)
        active_projects: Map of project_path → ProjectContext
    """
    
    host: str = "127.0.0.1"
    port: int = 8000
    transport: Literal["stdio", "sse"] = "stdio"
    auth_enabled: bool = False
    api_key: Optional[str] = None
    active_projects: Dict[str, "ProjectContext"] = field(default_factory=dict)
    _app: Optional[FastMCP] = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.auth_enabled and not self.api_key:
            raise ValueError(
                "API key authentication enabled but no API key provided. "
                "Either set api_key or disable auth_enabled."
            )
        
        if self.transport not in ("stdio", "sse"):
            raise ValueError(
                f"Invalid transport '{self.transport}'. "
                "Must be 'stdio' or 'sse'."
            )
        
        # Load host/port from environment if not explicitly set
        if self.host == "127.0.0.1" and "MCP_SERVER_HOST" in os.environ:
            self.host = os.environ["MCP_SERVER_HOST"]
        
        if self.port == 8000 and "MCP_SERVER_PORT" in os.environ:
            try:
                self.port = int(os.environ["MCP_SERVER_PORT"])
            except ValueError:
                raise ValueError(
                    f"Invalid MCP_SERVER_PORT: {os.environ['MCP_SERVER_PORT']}. "
                    "Must be an integer."
                )
        
        # Initialize FastMCP app
        self._app = FastMCP("Spec Kitty MCP Server")
        
        # Register all MCP tools
        self._register_tools()
    
    def _check_port_available(self, host: str, port: int) -> bool:
        """
        Check if port is available for binding.
        
        Args:
            host: Host address to check
            port: Port number to check
            
        Returns:
            True if port is available, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                return True
        except OSError:
            return False
    
    def _register_tools(self):
        """Register all MCP tools with the server."""
        from specify_cli.mcp.tools import workspace_operations
        
        # Register workspace operations tool
        self.register_tool(
            name="workspace_operations",
            description="Create and manage git worktrees for work packages",
            handler=workspace_operations
        )
    
    def start(self):
        """
        Start the MCP server with configured transport.
        
        Raises:
            RuntimeError: If port unavailable (SSE/HTTP) or FastMCP fails to start
        """
        if not self._app:
            raise RuntimeError("FastMCP app not initialized. This should not happen.")
        
        if self.transport == "stdio":
            # Stdio transport:
            # - Used by Claude Desktop, Cursor, and other local MCP clients
            # - Communicates via stdin/stdout (JSON-RPC messages)
            # - No network binding required (host/port ignored)
            # - Ideal for trusted local development environments
            try:
                self._app.run()  # STDIO is the default transport
            except Exception as e:
                raise RuntimeError(f"Failed to start MCP server with stdio transport: {e}") from e
        
        elif self.transport == "sse":
            # SSE transport:
            # - Legacy transport (use HTTP for new projects)
            # - Used by web-based MCP clients
            # - HTTP server with Server-Sent Events for streaming
            # - Binds to host:port (network accessible)
            # - Requires port availability check
            if not self._check_port_available(self.host, self.port):
                raise RuntimeError(
                    f"Port {self.port} already in use. "
                    f"Choose a different port or stop the conflicting service."
                )
            
            try:
                self._app.run(transport="sse", host=self.host, port=self.port)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to start MCP server on {self.host}:{self.port}: {e}"
                ) from e
    
    def register_tool(self, name: str, description: str, handler):
        """
        Register an MCP tool with the server.
        
        Args:
            name: Tool name (e.g., "feature_operations")
            description: Human-readable tool description
            handler: Callable that executes the tool operation
        """
        if not self._app:
            raise RuntimeError("FastMCP app not initialized")
        
        # FastMCP uses decorators, but we'll register programmatically
        # This will be expanded in WP02 when implementing actual tools
        self._app.tool(name=name, description=description)(handler)
