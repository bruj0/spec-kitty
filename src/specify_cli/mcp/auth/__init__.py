"""
Optional API key authentication for MCP server.

Provides configurable authentication layer for securing MCP server
access when running in network-accessible modes (SSE transport).
"""

from .api_key import (
    APIKeyError,
    APIKeyLowEntropyError,
    APIKeyTooShortError,
    APIKeyValidator,
    MIN_API_KEY_LENGTH,
    generate_api_key,
    load_api_key_from_env,
    validate_api_key_strength,
    verify_api_key,
)
from .middleware import (
    AuthMiddlewareManager,
    AuthenticationError,
    create_auth_middleware,
)

__all__ = [
    # API Key validation
    "APIKeyError",
    "APIKeyLowEntropyError",
    "APIKeyTooShortError",
    "APIKeyValidator",
    "MIN_API_KEY_LENGTH",
    "generate_api_key",
    "load_api_key_from_env",
    "validate_api_key_strength",
    "verify_api_key",
    # Middleware
    "AuthMiddlewareManager",
    "AuthenticationError",
    "create_auth_middleware",
]
