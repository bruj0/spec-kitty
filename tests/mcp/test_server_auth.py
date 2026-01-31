"""
Integration tests for MCP server authentication.

Tests authentication configuration, server startup with auth enabled,
and end-to-end authentication flows.
"""

import pytest

from specify_cli.mcp.server import MCPServer
from specify_cli.mcp.auth import APIKeyValidator


class TestServerAuthConfiguration:
    """Test MCPServer authentication configuration."""
    
    def test_server_default_auth_disabled(self):
        """Server should have authentication disabled by default."""
        server = MCPServer()
        assert server.auth_enabled is False
        assert server.api_key is None
    
    def test_server_auth_enabled_requires_api_key(self):
        """Server with auth enabled must have API key."""
        with pytest.raises(ValueError) as exc_info:
            MCPServer(auth_enabled=True, api_key=None)
        
        assert "API key" in str(exc_info.value)
        assert "no API key provided" in str(exc_info.value).lower()
    
    def test_server_auth_enabled_with_api_key(self):
        """Server should accept auth_enabled=True with valid API key."""
        api_key = "valid-test-api-key-with-sufficient-length-and-entropy"
        server = MCPServer(auth_enabled=True, api_key=api_key)
        
        assert server.auth_enabled is True
        assert server.api_key == api_key
    
    def test_server_auth_disabled_allows_no_key(self):
        """Server with auth disabled doesn't require API key."""
        server = MCPServer(auth_enabled=False, api_key=None)
        
        assert server.auth_enabled is False
        assert server.api_key is None
    
    def test_server_auth_manager_created(self):
        """Server should create AuthMiddlewareManager on initialization."""
        api_key = "valid-test-api-key-with-sufficient-length-and-entropy"
        server = MCPServer(auth_enabled=True, api_key=api_key)
        
        auth_manager = server.get_auth_middleware()
        assert auth_manager is not None
        assert auth_manager.enabled is True
    
    def test_server_auth_manager_disabled(self):
        """Server should create disabled AuthMiddlewareManager when auth off."""
        server = MCPServer(auth_enabled=False)
        
        auth_manager = server.get_auth_middleware()
        assert auth_manager is not None
        assert auth_manager.enabled is False


class TestServerToolRegistration:
    """Test tool registration with authentication."""
    
    @pytest.mark.asyncio
    async def test_tool_registration_applies_auth_when_enabled(self):
        """Tools registered should have auth middleware applied when enabled."""
        api_key = "valid-test-api-key-with-sufficient-length-and-entropy"
        server = MCPServer(auth_enabled=True, api_key=api_key)
        
        # Create a test handler
        async def test_tool_handler(arg: str):
            return f"Result: {arg}"
        
        # Register tool (this should apply auth middleware)
        server.register_tool(
            name="test_tool",
            description="Test tool for authentication",
            handler=test_tool_handler
        )
        
        # Note: We can't directly test the registered tool without
        # FastMCP's internal machinery, but we verify registration succeeds
        assert server._app is not None
    
    @pytest.mark.asyncio
    async def test_tool_registration_no_auth_when_disabled(self):
        """Tools registered should not have auth when disabled."""
        server = MCPServer(auth_enabled=False)
        
        async def test_tool_handler(arg: str):
            return f"Result: {arg}"
        
        # Should register successfully without requiring authentication
        server.register_tool(
            name="test_tool",
            description="Test tool without auth",
            handler=test_tool_handler
        )
        
        assert server._app is not None


class TestServerEnvironmentVariables:
    """Test server configuration from environment variables."""
    
    def test_api_key_from_env_not_loaded_automatically(self, monkeypatch):
        """Server should not automatically load API key from env."""
        # This is intentional - API key must be explicitly passed
        monkeypatch.setenv("SPEC_KITTY_API_KEY", "env-api-key-test")
        
        server = MCPServer(auth_enabled=False)
        
        # API key from env should NOT be used automatically
        # (user must explicitly load it via load_api_key_from_env())
        assert server.api_key is None
    
    def test_host_from_env(self, monkeypatch):
        """Server should load host from MCP_SERVER_HOST env var."""
        monkeypatch.setenv("MCP_SERVER_HOST", "0.0.0.0")
        
        server = MCPServer()
        assert server.host == "0.0.0.0"
    
    def test_port_from_env(self, monkeypatch):
        """Server should load port from MCP_SERVER_PORT env var."""
        monkeypatch.setenv("MCP_SERVER_PORT", "9000")
        
        server = MCPServer()
        assert server.port == 9000
    
    def test_invalid_port_from_env_raises_error(self, monkeypatch):
        """Invalid port in env var should raise ValueError."""
        monkeypatch.setenv("MCP_SERVER_PORT", "invalid")
        
        with pytest.raises(ValueError) as exc_info:
            MCPServer()
        
        assert "MCP_SERVER_PORT" in str(exc_info.value)
        assert "integer" in str(exc_info.value).lower()


class TestServerStartupLogging:
    """Test authentication status logging during server startup."""
    
    def test_auth_status_logged_when_enabled(self, caplog):
        """Server should log authentication status when enabled."""
        import logging
        
        api_key = "valid-test-api-key-with-sufficient-length-and-entropy"
        server = MCPServer(auth_enabled=True, api_key=api_key)
        
        # The actual start() method would log, but we can't call it
        # in tests without starting a real server. Instead, we verify
        # the auth manager can log status.
        auth_manager = server.get_auth_middleware()
        logger = logging.getLogger("test")
        
        with caplog.at_level(logging.INFO):
            auth_manager.log_status(logger)
        
        assert "Authentication enabled" in caplog.text
    
    def test_auth_status_logged_when_disabled(self, caplog):
        """Server should log authentication status when disabled."""
        import logging
        
        server = MCPServer(auth_enabled=False)
        
        auth_manager = server.get_auth_middleware()
        logger = logging.getLogger("test")
        
        with caplog.at_level(logging.INFO):
            auth_manager.log_status(logger)
        
        assert "Authentication disabled" in caplog.text


class TestAuthenticationWithMultipleTransports:
    """Test authentication works with both stdio and SSE transports."""
    
    def test_auth_with_stdio_transport(self):
        """Authentication should work with stdio transport."""
        api_key = "valid-test-api-key-with-sufficient-length-and-entropy"
        server = MCPServer(
            transport="stdio",
            auth_enabled=True,
            api_key=api_key
        )
        
        assert server.transport == "stdio"
        assert server.auth_enabled is True
    
    def test_auth_with_sse_transport(self):
        """Authentication should work with SSE transport."""
        api_key = "valid-test-api-key-with-sufficient-length-and-entropy"
        server = MCPServer(
            transport="sse",
            host="127.0.0.1",
            port=8000,
            auth_enabled=True,
            api_key=api_key
        )
        
        assert server.transport == "sse"
        assert server.auth_enabled is True
    
    def test_auth_disabled_with_stdio(self):
        """Authentication can be disabled with stdio (trusted local)."""
        server = MCPServer(transport="stdio", auth_enabled=False)
        
        assert server.transport == "stdio"
        assert server.auth_enabled is False
    
    def test_auth_disabled_with_sse(self):
        """Authentication can be disabled with SSE (development mode)."""
        server = MCPServer(
            transport="sse",
            host="127.0.0.1",
            port=8000,
            auth_enabled=False
        )
        
        assert server.transport == "sse"
        assert server.auth_enabled is False


class TestAPIKeyValidatorIntegration:
    """Test integration between server and APIKeyValidator."""
    
    def test_server_uses_validator_for_auth(self):
        """Server should use APIKeyValidator for authentication."""
        api_key = "valid-test-api-key-with-sufficient-length-and-entropy"
        server = MCPServer(auth_enabled=True, api_key=api_key)
        
        auth_manager = server.get_auth_middleware()
        
        # Auth manager should have a validator
        assert hasattr(auth_manager, 'validator')
        assert auth_manager.validator is not None
        
        # Validator should validate the configured key
        assert auth_manager.validator.validate(api_key) is True
        assert auth_manager.validator.validate("wrong-key-here") is False
