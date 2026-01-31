"""Tests for SSE transport functionality."""

from specify_cli.mcp.server import MCPServer


def test_sse_transport_initialization():
    """Test that SSE transport can be configured."""
    server = MCPServer(transport="sse", host="127.0.0.1", port=8001)
    assert server.transport == "sse"
    assert server.host == "127.0.0.1"
    assert server.port == 8001
    assert server._app is not None


def test_sse_requires_available_port():
    """Test that SSE transport checks port availability."""
    server = MCPServer(transport="sse", host="127.0.0.1", port=8002)
    # Just verify the port check method exists and works
    # Actual port availability depends on system state
    result = server._check_port_available("127.0.0.1", 8002)
    assert isinstance(result, bool)


def test_sse_port_conflict_detection():
    """Test that port conflict is detected."""
    import socket
    
    server = MCPServer(transport="sse", host="127.0.0.1", port=8003)
    
    # Bind to port to simulate conflict
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 8003))
        s.listen(1)
        
        # Now the port should be unavailable
        assert not server._check_port_available("127.0.0.1", 8003)
