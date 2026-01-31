"""Tests for stdio transport functionality."""

from specify_cli.mcp.server import MCPServer


def test_stdio_transport_initialization():
    """Test that stdio transport can be configured."""
    server = MCPServer(transport="stdio")
    assert server.transport == "stdio"
    assert server._app is not None


def test_stdio_ignores_host_port():
    """Test that stdio transport ignores host/port settings."""
    # Stdio doesn't use network, so host/port should be allowed but ignored
    server = MCPServer(transport="stdio", host="0.0.0.0", port=9999)
    assert server.transport == "stdio"
    # Server still stores these but won't use them
    assert server.host == "0.0.0.0"
    assert server.port == 9999
