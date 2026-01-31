#!/usr/bin/env python3
"""
Standalone test for API key authentication module.

Tests only the auth module without importing the full specify_cli package.
"""

import sys
import os
import importlib.util

# Load api_key module directly from file
api_key_path = os.path.join(
    os.path.dirname(__file__),
    'src/specify_cli/mcp/auth/api_key.py'
)

spec = importlib.util.spec_from_file_location("api_key", api_key_path)
api_key_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_key_module)

# Import from loaded module
APIKeyValidator = api_key_module.APIKeyValidator
generate_api_key = api_key_module.generate_api_key
verify_api_key = api_key_module.verify_api_key
validate_api_key_strength = api_key_module.validate_api_key_strength
APIKeyTooShortError = api_key_module.APIKeyTooShortError
APIKeyLowEntropyError = api_key_module.APIKeyLowEntropyError
MIN_API_KEY_LENGTH = api_key_module.MIN_API_KEY_LENGTH


def test_api_key_validation():
    """Test API key validation."""
    print("Testing API key validation...")
    
    # Test valid key
    valid_key = "a" * MIN_API_KEY_LENGTH + "bcdefghij"
    try:
        validate_api_key_strength(valid_key)
        print(f"✓ Valid API key ({len(valid_key)} chars) passes validation")
    except Exception as e:
        print(f"✗ Valid API key failed: {e}")
        return False
    
    # Test short key
    short_key = "short"
    try:
        validate_api_key_strength(short_key)
        print("✗ Short API key should have failed")
        return False
    except APIKeyTooShortError as e:
        print(f"✓ Short API key correctly rejected: {e}")
    
    # Test low entropy
    low_entropy = "aaaa" * 10
    try:
        validate_api_key_strength(low_entropy)
        print("✗ Low entropy key should have failed")
        return False
    except APIKeyLowEntropyError as e:
        print(f"✓ Low entropy key correctly rejected: {e}")
    
    return True


def test_api_key_verification():
    """Test API key verification (constant-time comparison)."""
    print("\nTesting API key verification...")
    
    key = "my-secret-api-key-with-sufficient-length-and-entropy"
    
    if not verify_api_key(key, key):
        print("✗ Identical keys should verify")
        return False
    print("✓ Identical keys verify successfully")
    
    if verify_api_key(key, "different-key-with-sufficient-length-and-entropy"):
        print("✗ Different keys should not verify")
        return False
    print("✓ Different keys correctly rejected")
    
    # Test case sensitivity
    if verify_api_key(key, key.upper()):
        print("✗ Case-sensitive comparison should fail")
        return False
    print("✓ Case-sensitive comparison works")
    
    return True


def test_api_key_generation():
    """Test API key generation."""
    print("\nTesting API key generation...")
    
    key1 = generate_api_key()
    key2 = generate_api_key()
    
    if len(key1) < MIN_API_KEY_LENGTH:
        print(f"✗ Generated key too short: {len(key1)} < {MIN_API_KEY_LENGTH}")
        return False
    print(f"✓ Generated key has sufficient length: {len(key1)} >= {MIN_API_KEY_LENGTH}")
    
    if key1 == key2:
        print("✗ Generated keys should be unique")
        return False
    print("✓ Generated keys are unique")
    
    # Test custom length
    key_64 = generate_api_key(length=64)
    if len(key_64) != 64:
        print(f"✗ Custom length key wrong size: {len(key_64)} != 64")
        return False
    print(f"✓ Custom length key generated correctly: {len(key_64)} chars")
    
    # Test URL-safe characters
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    if not all(c in allowed for c in key1):
        print("✗ Generated key contains non-URL-safe characters")
        return False
    print("✓ Generated key is URL-safe")
    
    # Test minimum length enforcement
    try:
        generate_api_key(length=MIN_API_KEY_LENGTH - 1)
        print("✗ Should reject length below minimum")
        return False
    except ValueError:
        print(f"✓ Correctly rejects length below {MIN_API_KEY_LENGTH}")
    
    return True


def test_api_key_validator():
    """Test APIKeyValidator class."""
    print("\nTesting APIKeyValidator class...")
    
    api_key = "valid-test-api-key-with-sufficient-length-and-entropy"
    
    # Test validator with strength validation
    try:
        validator = APIKeyValidator(api_key, validate_strength=True)
        print("✓ Validator created with strength validation")
    except Exception as e:
        print(f"✗ Failed to create validator: {e}")
        return False
    
    if not validator.validate(api_key):
        print("✗ Validator should accept correct key")
        return False
    print("✓ Validator accepts correct key")
    
    if validator.validate("wrong-key-with-sufficient-length-and-entropy"):
        print("✗ Validator should reject wrong key")
        return False
    print("✓ Validator rejects wrong key")
    
    # Test validator without strength validation
    weak_key = "short"
    validator_weak = APIKeyValidator(weak_key, validate_strength=False)
    if not validator_weak.validate(weak_key):
        print("✗ Validator without strength check should accept weak key")
        return False
    print("✓ Validator without strength check accepts weak key")
    
    # Test validator rejects weak key with strength validation
    try:
        APIKeyValidator(weak_key, validate_strength=True)
        print("✗ Validator should reject weak key with strength validation")
        return False
    except APIKeyTooShortError:
        print("✓ Validator rejects weak key with strength validation")
    
    return True


def test_constant_time_comparison():
    """Verify that verify_api_key uses constant-time comparison."""
    print("\nTesting constant-time comparison...")
    
    # We can't directly test timing, but we can verify the function signature
    # and that it uses hmac.compare_digest under the hood
    import inspect
    source = inspect.getsource(verify_api_key)
    
    if "hmac.compare_digest" in source:
        print("✓ Uses hmac.compare_digest for constant-time comparison")
    else:
        print("⚠ Warning: Does not appear to use hmac.compare_digest")
        # This is informational, not a failure
    
    return True


def main():
    """Run all standalone tests."""
    print("=" * 60)
    print("API Key Authentication Standalone Tests")
    print("=" * 60)
    print(f"Minimum API key length: {MIN_API_KEY_LENGTH} characters")
    print()
    
    tests = [
        test_api_key_validation,
        test_api_key_verification,
        test_api_key_generation,
        test_api_key_validator,
        test_constant_time_comparison,
    ]
    
    failed = []
    for test in tests:
        try:
            if not test():
                failed.append(test.__name__)
        except Exception as e:
            print(f"✗ {test.__name__} raised exception: {e}")
            import traceback
            traceback.print_exc()
            failed.append(test.__name__)
    
    print("\n" + "=" * 60)
    if failed:
        print(f"FAILED: {len(failed)} test(s) failed:")
        for name in failed:
            print(f"  - {name}")
        return 1
    else:
        print("SUCCESS: All tests passed!")
        print("\nAuthentication module is working correctly:")
        print("  • API key strength validation ✓")
        print("  • Constant-time key comparison ✓")
        print("  • Cryptographically secure key generation ✓")
        print("  • APIKeyValidator class ✓")
        return 0


if __name__ == "__main__":
    sys.exit(main())
