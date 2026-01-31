"""
Authentication middleware for FastMCP server.

Provides request-level authentication using API keys passed in
MCP connection metadata or request headers.
"""

import logging
from functools import wraps
from typing import Any, Callable, Optional

from .api_key import APIKeyValidator

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication required"):
        self.message = message
        self.status_code = 401
        super().__init__(message)


def create_auth_middleware(
    validator: APIKeyValidator,
    enabled: bool = True,
    header_name: str = "X-API-Key",
) -> Callable:
    """
    Create authentication middleware for FastMCP tools.
    
    The middleware checks for an API key in:
    1. Request headers (X-API-Key by default)
    2. MCP connection metadata (api_key field)
    
    If authentication is disabled, all requests pass through.
    If authentication is enabled but key is invalid, raises AuthenticationError.
    
    Args:
        validator: APIKeyValidator instance with expected key
        enabled: Whether authentication is enabled
        header_name: HTTP header name for API key (default: "X-API-Key")
        
    Returns:
        Middleware function that can wrap tool handlers
        
    Example:
        validator = APIKeyValidator("my-secret-key")
        auth_middleware = create_auth_middleware(validator, enabled=True)
        
        @auth_middleware
        async def my_tool(arg1: str, arg2: int):
            # Tool implementation
            pass
    """
    
    def middleware(handler: Callable) -> Callable:
        """Wrap a tool handler with authentication check."""
        
        @wraps(handler)
        async def wrapped(*args, **kwargs):
            """Execute handler with authentication check."""
            
            # If authentication is disabled, pass through
            if not enabled:
                return await handler(*args, **kwargs)
            
            # Try to extract API key from context
            # Note: FastMCP provides request context differently depending on transport
            # For stdio: Connection metadata in initial handshake
            # For SSE/HTTP: HTTP headers
            
            api_key = None
            
            # Method 1: Check kwargs for injected context (FastMCP pattern)
            if "_context" in kwargs:
                context = kwargs["_context"]
                
                # Try headers first (SSE/HTTP transport)
                if hasattr(context, "headers") and header_name in context.headers:
                    api_key = context.headers[header_name]
                
                # Try connection metadata (stdio transport)
                elif hasattr(context, "metadata") and "api_key" in context.metadata:
                    api_key = context.metadata["api_key"]
            
            # Method 2: Check kwargs directly (may be passed by client)
            if not api_key and "api_key" in kwargs:
                api_key = kwargs.pop("api_key")  # Remove from kwargs so handler doesn't see it
            
            # If no API key found, reject
            if not api_key:
                logger.warning("Authentication failed: No API key provided")
                raise AuthenticationError(
                    "Authentication required. Please configure your MCP client "
                    "with a valid API key."
                )
            
            # Validate API key
            if not validator.validate(api_key):
                logger.warning("Authentication failed: Invalid API key")
                raise AuthenticationError(
                    "Authentication failed. Invalid API key."
                )
            
            # Authentication successful, proceed to handler
            logger.debug("Authentication successful")
            return await handler(*args, **kwargs)
        
        return wrapped
    
    return middleware


class AuthMiddlewareManager:
    """
    Manages authentication middleware for all MCP tools.
    
    Provides a central place to configure and apply authentication
    to all registered tools.
    
    Example:
        manager = AuthMiddlewareManager(
            api_key="my-secret-key",
            enabled=True
        )
        
        # Apply to tool registration
        @manager.protect
        async def feature_operations(action: str, project_path: str):
            # Tool implementation
            pass
    """
    
    def __init__(self, api_key: Optional[str] = None, enabled: bool = False):
        """
        Initialize authentication manager.
        
        Args:
            api_key: Expected API key (required if enabled=True)
            enabled: Whether authentication is enabled
            
        Raises:
            ValueError: If enabled=True but api_key is None
        """
        self.enabled = enabled
        
        if enabled:
            if not api_key:
                raise ValueError(
                    "API key authentication enabled but no API key provided"
                )
            self.validator = APIKeyValidator(api_key, validate_strength=True)
            self.middleware = create_auth_middleware(self.validator, enabled=True)
        else:
            self.validator = None
            self.middleware = lambda f: f  # No-op middleware when disabled
    
    def protect(self, handler: Callable) -> Callable:
        """
        Apply authentication middleware to a tool handler.
        
        Args:
            handler: Tool handler function to protect
            
        Returns:
            Wrapped handler with authentication check
        """
        return self.middleware(handler)
    
    def log_status(self, logger_instance: logging.Logger) -> None:
        """
        Log authentication status to the provided logger.
        
        Args:
            logger_instance: Logger to write status to
        """
        if self.enabled:
            logger_instance.info("✓ Authentication enabled (API key required)")
        else:
            logger_instance.info("ℹ Authentication disabled (local trusted mode)")
