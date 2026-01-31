"""
Tests for API key authentication module.

Verifies API key validation, generation, and secure comparison
against timing attacks.
"""

import os
import pytest

from specify_cli.mcp.auth.api_key import (
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


class TestAPIKeyValidation:
    """Test API key strength validation."""
    
    def test_valid_api_key_passes(self):
        """Valid API key should pass validation."""
        valid_key = "a" * MIN_API_KEY_LENGTH + "bcdefghij"  # 32+ chars, diverse
        validate_api_key_strength(valid_key)  # Should not raise
    
    def test_short_api_key_fails(self):
        """API key shorter than minimum should fail."""
        short_key = "a" * (MIN_API_KEY_LENGTH - 1)
        
        with pytest.raises(APIKeyTooShortError) as exc_info:
            validate_api_key_strength(short_key)
        
        assert str(MIN_API_KEY_LENGTH) in str(exc_info.value)
        assert str(len(short_key)) in str(exc_info.value)
    
    def test_low_entropy_fails(self):
        """API key with low entropy should fail."""
        # 32 characters but only 5 unique chars
        low_entropy_key = "aaaabbbbccccddddeeee" * 2
        
        with pytest.raises(APIKeyLowEntropyError) as exc_info:
            validate_api_key_strength(low_entropy_key)
        
        assert "entropy" in str(exc_info.value).lower()
    
    def test_exactly_min_length_passes(self):
        """API key exactly at minimum length with good entropy should pass."""
        key = "abcdefghij" * 4  # Exactly 40 chars, 10 unique
        validate_api_key_strength(key)  # Should not raise


class TestAPIKeyVerification:
    """Test constant-time API key comparison."""
    
    def test_matching_keys_return_true(self):
        """Identical API keys should verify successfully."""
        key = "my-secret-api-key-with-sufficient-length-and-entropy-123"
        assert verify_api_key(key, key) is True
    
    def test_non_matching_keys_return_false(self):
        """Different API keys should not verify."""
        key1 = "api-key-1234567890abcdefghijklmnopqrstuvwxyz"
        key2 = "api-key-different-890abcdefghijklmnopqrstuvwxyz"
        assert verify_api_key(key1, key2) is False
    
    def test_case_sensitive_comparison(self):
        """API key comparison should be case-sensitive."""
        key_lower = "api-key-abcdefghijklmnopqrstuvwxyz1234567890"
        key_upper = "API-KEY-ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        assert verify_api_key(key_lower, key_upper) is False
    
    def test_whitespace_matters(self):
        """Trailing whitespace should cause verification to fail."""
        key = "api-key-abcdefghijklmnopqrstuvwxyz1234567890"
        key_with_space = key + " "
        assert verify_api_key(key, key_with_space) is False


class TestAPIKeyGeneration:
    """Test cryptographically secure API key generation."""
    
    def test_generated_key_meets_min_length(self):
        """Generated key should meet minimum length."""
        key = generate_api_key()
        assert len(key) >= MIN_API_KEY_LENGTH
    
    def test_generated_key_has_requested_length(self):
        """Generated key should have requested length."""
        length = 64
        key = generate_api_key(length=length)
        assert len(key) == length
    
    def test_generated_keys_are_unique(self):
        """Multiple generated keys should be different."""
        keys = [generate_api_key() for _ in range(10)]
        assert len(set(keys)) == 10  # All unique
    
    def test_generated_key_is_url_safe(self):
        """Generated key should be URL-safe (alphanumeric + - _)."""
        key = generate_api_key()
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        assert all(c in allowed for c in key)
    
    def test_short_length_raises_error(self):
        """Generating key shorter than minimum should raise error."""
        with pytest.raises(ValueError) as exc_info:
            generate_api_key(length=MIN_API_KEY_LENGTH - 1)
        
        assert str(MIN_API_KEY_LENGTH) in str(exc_info.value)


class TestLoadAPIKeyFromEnv:
    """Test loading API key from environment variables."""
    
    def test_loads_key_from_env(self, monkeypatch):
        """Should load API key from SPEC_KITTY_API_KEY env var."""
        expected_key = "my-test-api-key-from-environment-variable"
        monkeypatch.setenv("SPEC_KITTY_API_KEY", expected_key)
        
        actual_key = load_api_key_from_env()
        assert actual_key == expected_key
    
    def test_returns_none_when_not_set(self, monkeypatch):
        """Should return None when env var not set."""
        monkeypatch.delenv("SPEC_KITTY_API_KEY", raising=False)
        
        key = load_api_key_from_env()
        assert key is None


class TestAPIKeyValidator:
    """Test APIKeyValidator class."""
    
    def test_validator_requires_strong_key_by_default(self):
        """Validator should reject weak keys by default."""
        weak_key = "short"
        
        with pytest.raises(APIKeyTooShortError):
            APIKeyValidator(weak_key)
    
    def test_validator_accepts_weak_key_when_disabled(self):
        """Validator should accept weak keys when validation disabled."""
        weak_key = "short"
        validator = APIKeyValidator(weak_key, validate_strength=False)
        assert validator is not None
    
    def test_validator_validates_correct_key(self):
        """Validator should accept correct API key."""
        expected_key = "correct-api-key-with-sufficient-length-and-entropy"
        validator = APIKeyValidator(expected_key)
        
        assert validator.validate(expected_key) is True
    
    def test_validator_rejects_incorrect_key(self):
        """Validator should reject incorrect API key."""
        expected_key = "correct-api-key-with-sufficient-length-and-entropy"
        wrong_key = "wrong-api-key-with-different-content-here-entropy"
        
        validator = APIKeyValidator(expected_key)
        assert validator.validate(wrong_key) is False
    
    def test_validator_is_case_sensitive(self):
        """Validator should perform case-sensitive comparison."""
        key_lower = "api-key-abcdefghijklmnopqrstuvwxyz1234567890"
        key_upper = "API-KEY-ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        
        validator = APIKeyValidator(key_lower)
        assert validator.validate(key_upper) is False


class TestAPIKeyErrorHierarchy:
    """Test exception hierarchy."""
    
    def test_specific_errors_inherit_from_base(self):
        """Specific API key errors should inherit from APIKeyError."""
        assert issubclass(APIKeyTooShortError, APIKeyError)
        assert issubclass(APIKeyLowEntropyError, APIKeyError)
    
    def test_can_catch_all_errors_with_base(self):
        """Should be able to catch all API key errors with base exception."""
        with pytest.raises(APIKeyError):
            validate_api_key_strength("short")
        
        with pytest.raises(APIKeyError):
            validate_api_key_strength("aaaa" * 10)  # Low entropy
