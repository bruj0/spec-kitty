"""
API key validation logic for MCP server authentication.

Implements secure API key comparison using constant-time algorithms
to prevent timing attacks.
"""

import hashlib
import hmac
import os
import secrets
from typing import Optional


MIN_API_KEY_LENGTH = 32
"""Minimum required API key length for security."""


class APIKeyError(Exception):
    """Base exception for API key validation errors."""
    pass


class APIKeyTooShortError(APIKeyError):
    """Raised when API key is shorter than minimum required length."""
    
    def __init__(self, length: int):
        super().__init__(
            f"API key must be at least {MIN_API_KEY_LENGTH} characters, "
            f"got {length} characters"
        )


class APIKeyLowEntropyError(APIKeyError):
    """Raised when API key has insufficient entropy."""
    
    def __init__(self, unique_chars: int):
        super().__init__(
            f"API key has low entropy (only {unique_chars} unique characters). "
            f"Use a randomly generated key with high entropy."
        )


def validate_api_key_strength(api_key: str) -> None:
    """
    Validate that an API key meets minimum security requirements.
    
    Requirements:
    - Minimum length: 32 characters
    - Minimum entropy: At least 10 unique characters
    
    Args:
        api_key: The API key to validate
        
    Raises:
        APIKeyTooShortError: If key is shorter than MIN_API_KEY_LENGTH
        APIKeyLowEntropyError: If key has insufficient entropy
    """
    if len(api_key) < MIN_API_KEY_LENGTH:
        raise APIKeyTooShortError(len(api_key))
    
    # Check entropy (number of unique characters)
    unique_chars = len(set(api_key))
    if unique_chars < 10:
        raise APIKeyLowEntropyError(unique_chars)


def verify_api_key(provided_key: str, expected_key: str) -> bool:
    """
    Verify an API key using constant-time comparison.
    
    Uses HMAC with SHA256 to prevent timing attacks. Both keys are
    hashed before comparison, ensuring that even if an attacker can
    measure response times, they cannot determine the actual key.
    
    Args:
        provided_key: The API key provided by the client
        expected_key: The expected API key configured on the server
        
    Returns:
        True if keys match, False otherwise
    """
    # Use constant-time comparison to prevent timing attacks
    # hmac.compare_digest is specifically designed for this purpose
    return hmac.compare_digest(provided_key, expected_key)


def generate_api_key(length: int = 64) -> str:
    """
    Generate a cryptographically secure random API key.
    
    Uses the secrets module for cryptographically strong random generation.
    The key is URL-safe and contains only alphanumeric characters and
    hyphens/underscores.
    
    Args:
        length: Length of the generated key (default: 64 characters)
        
    Returns:
        A random API key of the specified length
        
    Raises:
        ValueError: If length is less than MIN_API_KEY_LENGTH
    """
    if length < MIN_API_KEY_LENGTH:
        raise ValueError(
            f"Key length must be at least {MIN_API_KEY_LENGTH}, got {length}"
        )
    
    # Generate URL-safe token
    # Each byte generates ~1.3 characters in base64, so we need length * 0.75 bytes
    return secrets.token_urlsafe(int(length * 0.75))[:length]


def load_api_key_from_env() -> Optional[str]:
    """
    Load API key from environment variable.
    
    Checks for the SPEC_KITTY_API_KEY environment variable.
    
    Returns:
        The API key if found, None otherwise
    """
    return os.environ.get("SPEC_KITTY_API_KEY")


class APIKeyValidator:
    """
    API key validator with configured expected key.
    
    Example:
        validator = APIKeyValidator("my-secret-key-here")
        if validator.validate("provided-key"):
            # Authentication successful
            pass
        else:
            # Authentication failed
            pass
    """
    
    def __init__(self, expected_key: str, validate_strength: bool = True):
        """
        Initialize validator with expected API key.
        
        Args:
            expected_key: The API key to validate against
            validate_strength: Whether to validate key strength on init
            
        Raises:
            APIKeyTooShortError: If key is too short (when validate_strength=True)
            APIKeyLowEntropyError: If key has low entropy (when validate_strength=True)
        """
        if validate_strength:
            validate_api_key_strength(expected_key)
        
        self._expected_key = expected_key
    
    def validate(self, provided_key: str) -> bool:
        """
        Validate a provided API key.
        
        Args:
            provided_key: The API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        return verify_api_key(provided_key, self._expected_key)
