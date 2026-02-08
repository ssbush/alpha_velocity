#!/usr/bin/env python3
"""
CORS Configuration Test Script

Tests the CORS configuration to ensure it's working correctly
and validating origins properly.

Usage:
    python test_cors_config.py
"""

import os
import sys

# Set up environment for testing
os.environ['ENVIRONMENT'] = 'development'
os.environ['CORS_ORIGINS'] = 'http://localhost:3000,http://localhost:8080'

from backend.config.cors_config import (
    get_cors_origins,
    get_cors_settings,
    is_production,
    validate_origin,
    get_cors_config_info
)


def test_development_config():
    """Test development configuration"""
    print("\n" + "="*60)
    print("Testing Development Configuration")
    print("="*60)

    origins = get_cors_origins()
    print(f"✓ Origins loaded: {origins}")
    assert len(origins) == 2, "Should have 2 origins configured"

    assert not is_production(), "Should be in development mode"
    print("✓ Environment detected as development")

    settings = get_cors_settings()
    print(f"✓ CORS settings configured:")
    print(f"  - Origins: {len(settings['allow_origins'])}")
    print(f"  - Credentials: {settings['allow_credentials']}")
    print(f"  - Methods: {settings['allow_methods']}")
    print(f"  - Headers: {settings['allow_headers']}")
    print(f"  - Max Age: {settings['max_age']}")

    assert settings['allow_credentials'] == True
    print("✓ Credentials enabled")


def test_origin_validation():
    """Test origin validation"""
    print("\n" + "="*60)
    print("Testing Origin Validation")
    print("="*60)

    # Test allowed origin
    assert validate_origin('http://localhost:3000'), "Should allow configured origin"
    print("✓ Allowed origin validated correctly")

    # Test disallowed origin
    assert not validate_origin('https://evil-site.com'), "Should block unknown origin"
    print("✓ Unknown origin blocked correctly")


def test_production_blocking():
    """Test that production blocks wildcard origins"""
    print("\n" + "="*60)
    print("Testing Production Security")
    print("="*60)

    # Temporarily set to production
    original_env = os.environ.get('ENVIRONMENT')
    original_origins = os.environ.get('CORS_ORIGINS')

    try:
        os.environ['ENVIRONMENT'] = 'production'
        os.environ['CORS_ORIGINS'] = '*'

        # Import fresh to get new config
        from importlib import reload
        import backend.config.cors_config as cors_module
        reload(cors_module)

        # This should raise an error
        from fastapi import FastAPI
        app = FastAPI()

        try:
            cors_module.setup_cors(app)
            print("✗ FAILED: Production should block wildcard origins!")
            return False
        except ValueError as e:
            if "Wildcard CORS origins not allowed in production" in str(e):
                print("✓ Production correctly blocks wildcard origins")
                return True
            else:
                print(f"✗ Wrong error: {e}")
                return False

    finally:
        # Restore original environment
        if original_env:
            os.environ['ENVIRONMENT'] = original_env
        if original_origins:
            os.environ['CORS_ORIGINS'] = original_origins


def test_invalid_origin_format():
    """Test that invalid origin formats are rejected in production"""
    print("\n" + "="*60)
    print("Testing Invalid Origin Format Detection")
    print("="*60)

    original_env = os.environ.get('ENVIRONMENT')
    original_origins = os.environ.get('CORS_ORIGINS')

    try:
        os.environ['ENVIRONMENT'] = 'production'
        os.environ['CORS_ORIGINS'] = 'invalid-origin,another-bad-one'

        from importlib import reload
        import backend.config.cors_config as cors_module
        reload(cors_module)

        from fastapi import FastAPI
        app = FastAPI()

        try:
            cors_module.setup_cors(app)
            print("✗ FAILED: Should reject invalid origin formats!")
            return False
        except ValueError as e:
            if "Invalid origin format" in str(e):
                print("✓ Invalid origin format correctly rejected")
                return True
            else:
                print(f"✗ Wrong error: {e}")
                return False

    finally:
        if original_env:
            os.environ['ENVIRONMENT'] = original_env
        if original_origins:
            os.environ['CORS_ORIGINS'] = original_origins


def test_config_info():
    """Test configuration info retrieval"""
    print("\n" + "="*60)
    print("Testing Configuration Info")
    print("="*60)

    info = get_cors_config_info()
    print(f"✓ Configuration info retrieved:")
    for key, value in info.items():
        print(f"  - {key}: {value}")

    assert 'environment' in info
    assert 'is_production' in info
    assert 'origins_count' in info
    print("✓ All configuration info fields present")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("CORS Configuration Test Suite")
    print("="*60)

    tests = [
        ("Development Config", test_development_config),
        ("Origin Validation", test_origin_validation),
        ("Production Security", test_production_blocking),
        ("Invalid Format Detection", test_invalid_origin_format),
        ("Config Info", test_config_info),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = test_func()
            if result is None:
                result = True  # Assume success if no return value

            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print("Test Results")
    print("="*60)
    print(f"✓ Passed: {passed}/{len(tests)}")
    print(f"✗ Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n🎉 All CORS configuration tests passed!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
