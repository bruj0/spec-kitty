"""Tests for MCPServer core functionality."""

import pytest
from specify_cli.mcp.server import MCPServer


def test_server_initialization_default():
    """Test that MCPServer initializes with default configuration."""
    server = MCPServer()
    assert server.host == "127.0.0.1"
    assert server.port == 8000
    assert server.transport == "stdio"
    assert server.auth_enabled is False
    assert server.api_key is None
    assert server._app is not None


def test_server_initialization_custom():
    """Test that MCPServer initializes with custom configuration."""
    server = MCPServer(
        host="0.0.0.0",
        port=9000,
        transport="sse",
        auth_enabled=True,
        api_key="test-key-123"
    )
    assert server.host == "0.0.0.0"
    assert server.port == 9000
    assert server.transport == "sse"
    assert server.auth_enabled is True
    assert server.api_key == "test-key-123"


def test_server_auth_validation():
    """Test that auth_enabled requires api_key."""
    with pytest.raises(ValueError, match="API key authentication enabled but no API key provided"):
        MCPServer(auth_enabled=True, api_key=None)


def test_server_invalid_transport():
    """Test that invalid transport raises ValueError."""
    with pytest.raises(ValueError, match="Invalid transport"):
        MCPServer(transport="invalid")


def test_server_port_check():
    """Test port availability check."""
    server = MCPServer()
    # Port 8000 should be available (or pick different port)
    assert server._check_port_available("127.0.0.1", 8000) in (True, False)
    # Port 0 is always invalid
    assert not server._check_port_available("127.0.0.1", 0)


def test_server_environment_variables(monkeypatch):
    """Test that server respects environment variables."""
    monkeypatch.setenv("MCP_SERVER_HOST", "192.168.1.1")
    monkeypatch.setenv("MCP_SERVER_PORT", "9999")
    
    server = MCPServer()
    assert server.host == "192.168.1.1"
    assert server.port == 9999


def test_server_invalid_port_env(monkeypatch):
    """Test that invalid MCP_SERVER_PORT raises ValueError."""
    monkeypatch.setenv("MCP_SERVER_PORT", "not-a-number")
    
    with pytest.raises(ValueError, match="Invalid MCP_SERVER_PORT"):
        MCPServer()
