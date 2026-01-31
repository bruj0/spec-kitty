"""
Tests for authentication middleware.

Verifies that authentication middleware correctly protects MCP tools,
handles authentication headers, and provides proper error responses.
"""

import pytest
from unittest.mock import AsyncMock, Mock

from specify_cli.mcp.auth.api_key import APIKeyValidator
from specify_cli.mcp.auth.middleware import (
    AuthMiddlewareManager,
    AuthenticationError,
    create_auth_middleware,
)


class TestAuthenticationError:
    """Test AuthenticationError exception."""
    
    def test_default_message(self):
        """Should have default authentication required message."""
        error = AuthenticationError()
        assert "Authentication required" in str(error)
        assert error.status_code == 401
    
    def test_custom_message(self):
        """Should allow custom error message."""
        custom_msg = "Invalid API key provided"
        error = AuthenticationError(custom_msg)
        assert custom_msg in str(error)
        assert error.status_code == 401


class TestCreateAuthMiddleware:
    """Test create_auth_middleware function."""
    
    @pytest.fixture
    def valid_api_key(self):
        """Valid API key for testing."""
        return "test-api-key-with-sufficient-length-and-good-entropy"
    
    @pytest.fixture
    def validator(self, valid_api_key):
        """API key validator for testing."""
        return APIKeyValidator(valid_api_key, validate_strength=False)
    
    @pytest.mark.asyncio
    async def test_disabled_auth_allows_all_requests(self, validator):
        """When auth disabled, all requests should pass through."""
        middleware = create_auth_middleware(validator, enabled=False)
        
        @middleware
        async def test_handler(arg1: str):
            return f"Result: {arg1}"
        
        # Should succeed without API key
        result = await test_handler("test")
        assert result == "Result: test"
    
    @pytest.mark.asyncio
    async def test_enabled_auth_requires_api_key(self, validator, valid_api_key):
        """When auth enabled, requests must provide API key."""
        middleware = create_auth_middleware(validator, enabled=True)
        
        @middleware
        async def test_handler(arg1: str):
            return f"Result: {arg1}"
        
        # Should fail without API key
        with pytest.raises(AuthenticationError) as exc_info:
            await test_handler("test")
        
        assert "Authentication required" in str(exc_info.value)
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_valid_api_key_in_kwargs(self, validator, valid_api_key):
        """Should accept valid API key in kwargs."""
        middleware = create_auth_middleware(validator, enabled=True)
        
        @middleware
        async def test_handler(arg1: str):
            return f"Result: {arg1}"
        
        # Should succeed with valid API key in kwargs
        result = await test_handler("test", api_key=valid_api_key)
        assert result == "Result: test"
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self, validator):
        """Should reject invalid API key."""
        middleware = create_auth_middleware(validator, enabled=True)
        
        @middleware
        async def test_handler(arg1: str):
            return f"Result: {arg1}"
        
        # Should fail with invalid API key
        with pytest.raises(AuthenticationError) as exc_info:
            await test_handler("test", api_key="wrong-key-that-is-long-enough")
        
        assert "Invalid API key" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_api_key_from_context_headers(self, validator, valid_api_key):
        """Should extract API key from context headers (SSE/HTTP transport)."""
        middleware = create_auth_middleware(validator, enabled=True, header_name="X-API-Key")
        
        @middleware
        async def test_handler(arg1: str):
            return f"Result: {arg1}"
        
        # Mock context with headers
        context = Mock()
        context.headers = {"X-API-Key": valid_api_key}
        
        result = await test_handler("test", _context=context)
        assert result == "Result: test"
    
    @pytest.mark.asyncio
    async def test_api_key_from_context_metadata(self, validator, valid_api_key):
        """Should extract API key from context metadata (stdio transport)."""
        middleware = create_auth_middleware(validator, enabled=True)
        
        @middleware
        async def test_handler(arg1: str):
            return f"Result: {arg1}"
        
        # Mock context with metadata (stdio transport)
        context = Mock()
        context.metadata = {"api_key": valid_api_key}
        
        result = await test_handler("test", _context=context)
        assert result == "Result: test"
    
    @pytest.mark.asyncio
    async def test_custom_header_name(self, validator, valid_api_key):
        """Should support custom header names."""
        middleware = create_auth_middleware(
            validator,
            enabled=True,
            header_name="Authorization"
        )
        
        @middleware
        async def test_handler(arg1: str):
            return f"Result: {arg1}"
        
        context = Mock()
        context.headers = {"Authorization": valid_api_key}
        
        result = await test_handler("test", _context=context)
        assert result == "Result: test"
    
    @pytest.mark.asyncio
    async def test_api_key_removed_from_kwargs(self, validator, valid_api_key):
        """API key should be removed from kwargs before handler execution."""
        middleware = create_auth_middleware(validator, enabled=True)
        
        received_kwargs = {}
        
        @middleware
        async def test_handler(**kwargs):
            received_kwargs.update(kwargs)
            return "success"
        
        await test_handler(arg1="test", api_key=valid_api_key)
        
        # API key should not be passed to handler
        assert "api_key" not in received_kwargs
        assert received_kwargs["arg1"] == "test"


class TestAuthMiddlewareManager:
    """Test AuthMiddlewareManager class."""
    
    def test_manager_requires_api_key_when_enabled(self):
        """Manager should require API key when authentication enabled."""
        with pytest.raises(ValueError) as exc_info:
            AuthMiddlewareManager(api_key=None, enabled=True)
        
        assert "API key" in str(exc_info.value)
    
    def test_manager_allows_no_key_when_disabled(self):
        """Manager should allow missing API key when auth disabled."""
        manager = AuthMiddlewareManager(api_key=None, enabled=False)
        assert manager is not None
        assert manager.enabled is False
    
    def test_manager_validates_api_key_strength(self):
        """Manager should validate API key strength when enabled."""
        weak_key = "short"
        
        with pytest.raises(Exception):  # Will raise APIKeyTooShortError
            AuthMiddlewareManager(api_key=weak_key, enabled=True)
    
    @pytest.mark.asyncio
    async def test_protect_applies_middleware(self):
        """protect() should apply authentication middleware."""
        api_key = "valid-api-key-with-sufficient-length-and-entropy"
        manager = AuthMiddlewareManager(api_key=api_key, enabled=True)
        
        @manager.protect
        async def test_handler(arg1: str):
            return f"Result: {arg1}"
        
        # Should fail without API key
        with pytest.raises(AuthenticationError):
            await test_handler("test")
        
        # Should succeed with valid API key
        result = await test_handler("test", api_key=api_key)
        assert result == "Result: test"
    
    @pytest.mark.asyncio
    async def test_protect_no_op_when_disabled(self):
        """protect() should be no-op when auth disabled."""
        manager = AuthMiddlewareManager(api_key=None, enabled=False)
        
        @manager.protect
        async def test_handler(arg1: str):
            return f"Result: {arg1}"
        
        # Should succeed without API key
        result = await test_handler("test")
        assert result == "Result: test"
    
    def test_log_status_enabled(self, caplog):
        """log_status should log when authentication enabled."""
        import logging
        
        api_key = "valid-api-key-with-sufficient-length-and-entropy"
        manager = AuthMiddlewareManager(api_key=api_key, enabled=True)
        
        logger = logging.getLogger("test")
        with caplog.at_level(logging.INFO):
            manager.log_status(logger)
        
        assert "Authentication enabled" in caplog.text
        assert "API key required" in caplog.text
    
    def test_log_status_disabled(self, caplog):
        """log_status should log when authentication disabled."""
        import logging
        
        manager = AuthMiddlewareManager(api_key=None, enabled=False)
        
        logger = logging.getLogger("test")
        with caplog.at_level(logging.INFO):
            manager.log_status(logger)
        
        assert "Authentication disabled" in caplog.text
        assert "local trusted mode" in caplog.text.lower()


class TestMiddlewareIntegration:
    """Integration tests for authentication middleware."""
    
    @pytest.mark.asyncio
    async def test_multiple_tools_with_same_manager(self):
        """Multiple tools should share the same auth manager."""
        api_key = "shared-api-key-with-sufficient-length-and-entropy"
        manager = AuthMiddlewareManager(api_key=api_key, enabled=True)
        
        @manager.protect
        async def tool_a(arg: str):
            return f"Tool A: {arg}"
        
        @manager.protect
        async def tool_b(arg: int):
            return f"Tool B: {arg}"
        
        # Both tools should require authentication
        with pytest.raises(AuthenticationError):
            await tool_a("test")
        
        with pytest.raises(AuthenticationError):
            await tool_b(123)
        
        # Both should work with valid API key
        result_a = await tool_a("test", api_key=api_key)
        result_b = await tool_b(123, api_key=api_key)
        
        assert result_a == "Tool A: test"
        assert result_b == "Tool B: 123"
