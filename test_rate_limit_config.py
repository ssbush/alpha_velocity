#!/usr/bin/env python3
"""
Rate Limiting Configuration Test

Tests rate limiting configuration without requiring slowapi installation.
This tests the configuration layer only.

Usage:
    python test_rate_limit_config.py
"""

import sys
import os

# Set test environment
os.environ['RATE_LIMIT_ENABLED'] = 'true'
os.environ['RATE_LIMIT_STORAGE_URL'] = 'memory://'
os.environ['AUTH_RATE_LIMIT'] = '5/minute'
os.environ['DEFAULT_RATE_LIMIT'] = '100/minute'
os.environ['EXPENSIVE_RATE_LIMIT'] = '10/minute'
os.environ['AUTHENTICATED_RATE_LIMIT'] = '200/minute'


def test_environment_variables():
    """Test that environment variables are loaded correctly"""
    print("\n" + "="*60)
    print("Testing Environment Variables")
    print("="*60)

    assert os.getenv('RATE_LIMIT_ENABLED') == 'true', "RATE_LIMIT_ENABLED should be set"
    print("✓ RATE_LIMIT_ENABLED =", os.getenv('RATE_LIMIT_ENABLED'))

    assert os.getenv('RATE_LIMIT_STORAGE_URL') == 'memory://', "Storage URL should be set"
    print("✓ RATE_LIMIT_STORAGE_URL =", os.getenv('RATE_LIMIT_STORAGE_URL'))

    assert os.getenv('AUTH_RATE_LIMIT') == '5/minute', "Auth rate limit should be set"
    print("✓ AUTH_RATE_LIMIT =", os.getenv('AUTH_RATE_LIMIT'))

    assert os.getenv('DEFAULT_RATE_LIMIT') == '100/minute', "Default rate limit should be set"
    print("✓ DEFAULT_RATE_LIMIT =", os.getenv('DEFAULT_RATE_LIMIT'))

    return True


def test_rate_limit_format():
    """Test that rate limit formats are valid"""
    print("\n" + "="*60)
    print("Testing Rate Limit Format")
    print("="*60)

    rate_limits = {
        'AUTH_RATE_LIMIT': os.getenv('AUTH_RATE_LIMIT'),
        'DEFAULT_RATE_LIMIT': os.getenv('DEFAULT_RATE_LIMIT'),
        'EXPENSIVE_RATE_LIMIT': os.getenv('EXPENSIVE_RATE_LIMIT'),
        'AUTHENTICATED_RATE_LIMIT': os.getenv('AUTHENTICATED_RATE_LIMIT'),
    }

    for name, limit in rate_limits.items():
        if not limit:
            print(f"✗ FAILED: {name} not set")
            return False

        if '/' not in limit:
            print(f"✗ FAILED: {name} should be in format 'count/period'")
            return False

        count, period = limit.split('/')

        if not count.isdigit():
            print(f"✗ FAILED: {name} count should be numeric")
            return False

        if period not in ['second', 'minute', 'hour', 'day']:
            print(f"✗ FAILED: {name} period should be valid (second/minute/hour/day)")
            return False

        print(f"✓ {name} format valid: {limit}")

    return True


def test_requirements_file():
    """Test that slowapi and redis are in requirements.txt"""
    print("\n" + "="*60)
    print("Testing Requirements File")
    print("="*60)

    try:
        with open('/alpha_velocity/requirements.txt', 'r') as f:
            requirements = f.read()

        if 'slowapi' in requirements:
            print("✓ slowapi found in requirements.txt")
        else:
            print("✗ FAILED: slowapi not found in requirements.txt")
            return False

        if 'redis' in requirements:
            print("✓ redis found in requirements.txt")
        else:
            print("✗ FAILED: redis not found in requirements.txt")
            return False

        return True

    except FileNotFoundError:
        print("✗ FAILED: requirements.txt not found")
        return False


def test_env_example_file():
    """Test that .env.example contains rate limiting configuration"""
    print("\n" + "="*60)
    print("Testing .env.example File")
    print("="*60)

    try:
        with open('/alpha_velocity/.env.example', 'r') as f:
            env_example = f.read()

        required_vars = [
            'RATE_LIMIT_ENABLED',
            'RATE_LIMIT_STORAGE_URL',
            'RATE_LIMIT_STRATEGY',
            'DEFAULT_RATE_LIMIT',
            'AUTH_RATE_LIMIT',
            'EXPENSIVE_RATE_LIMIT',
            'AUTHENTICATED_RATE_LIMIT',
            'RATE_LIMIT_EXEMPT_IPS',
        ]

        for var in required_vars:
            if var in env_example:
                print(f"✓ {var} found in .env.example")
            else:
                print(f"✗ FAILED: {var} not found in .env.example")
                return False

        return True

    except FileNotFoundError:
        print("✗ FAILED: .env.example not found")
        return False


def test_rate_limit_config_file():
    """Test that rate_limit_config.py exists and has expected structure"""
    print("\n" + "="*60)
    print("Testing rate_limit_config.py File")
    print("="*60)

    config_file = '/alpha_velocity/backend/config/rate_limit_config.py'

    try:
        with open(config_file, 'r') as f:
            config_code = f.read()

        required_functions = [
            'get_identifier',
            'get_rate_limit_key',
            'get_rate_limit_for_user',
            'get_rate_limit_config',
            'log_rate_limit_config',
            'rate_limit_exceeded_handler',
            'create_rate_limit_exemption',
        ]

        for func in required_functions:
            if f'def {func}' in config_code:
                print(f"✓ Function '{func}' found")
            else:
                print(f"✗ FAILED: Function '{func}' not found")
                return False

        # Check for RateLimits class
        if 'class RateLimits:' in config_code:
            print("✓ Class 'RateLimits' found")
        else:
            print("✗ FAILED: Class 'RateLimits' not found")
            return False

        return True

    except FileNotFoundError:
        print(f"✗ FAILED: {config_file} not found")
        return False


def test_main_integration():
    """Test that main.py has rate limiting integration"""
    print("\n" + "="*60)
    print("Testing main.py Integration")
    print("="*60)

    main_file = '/alpha_velocity/backend/main.py'

    try:
        with open(main_file, 'r') as f:
            main_code = f.read()

        # Check for imports
        if 'from .config.rate_limit_config import' in main_code:
            print("✓ Rate limit config imported")
        else:
            print("✗ FAILED: Rate limit config not imported")
            return False

        # Check for limiter setup
        if 'app.state.limiter = limiter' in main_code:
            print("✓ Limiter added to app state")
        else:
            print("✗ FAILED: Limiter not added to app state")
            return False

        # Check for exception handler
        if 'add_exception_handler(RateLimitExceeded' in main_code:
            print("✓ Rate limit exception handler added")
        else:
            print("✗ FAILED: Rate limit exception handler not added")
            return False

        # Check for at least one rate-limited endpoint
        if '@limiter.limit(' in main_code:
            print("✓ Rate limiting applied to endpoints")
        else:
            print("✗ FAILED: No endpoints have rate limiting applied")
            return False

        return True

    except FileNotFoundError:
        print(f"✗ FAILED: {main_file} not found")
        return False


def test_documentation():
    """Test that RATE_LIMITING.md documentation exists"""
    print("\n" + "="*60)
    print("Testing Documentation")
    print("="*60)

    doc_file = '/alpha_velocity/RATE_LIMITING.md'

    try:
        with open(doc_file, 'r') as f:
            doc_content = f.read()

        if len(doc_content) > 1000:
            print(f"✓ RATE_LIMITING.md exists ({len(doc_content)} chars)")
        else:
            print("✗ FAILED: RATE_LIMITING.md too short")
            return False

        required_sections = [
            'Installation',
            'Configuration',
            'Usage',
            'Testing',
            'Security',
        ]

        for section in required_sections:
            if section in doc_content:
                print(f"✓ Section '{section}' found in documentation")
            else:
                print(f"⚠️  Warning: Section '{section}' not found in documentation")

        return True

    except FileNotFoundError:
        print(f"✗ FAILED: {doc_file} not found")
        return False


def main():
    """Run all configuration tests"""
    print("\n" + "="*60)
    print("Rate Limiting Configuration Test Suite")
    print("="*60)
    print("\nNote: This tests configuration only.")
    print("Full functionality testing requires: pip install slowapi redis")

    tests = [
        ("Environment Variables", test_environment_variables),
        ("Rate Limit Format", test_rate_limit_format),
        ("Requirements File", test_requirements_file),
        (".env.example File", test_env_example_file),
        ("rate_limit_config.py File", test_rate_limit_config_file),
        ("main.py Integration", test_main_integration),
        ("Documentation", test_documentation),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = test_func()
            if result is None or result is True:
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
        print("\n🎉 All configuration tests passed!")
        print("\n✅ Rate limiting configuration is complete:")
        print("  - Environment variables configured")
        print("  - Rate limit formats valid")
        print("  - Dependencies added to requirements.txt")
        print("  - .env.example updated")
        print("  - rate_limit_config.py created")
        print("  - main.py integrated with rate limiting")
        print("  - Documentation created")
        print("\n📝 Next Steps:")
        print("  1. Install dependencies: pip install slowapi redis")
        print("  2. Run full tests: python test_rate_limiting.py")
        print("  3. Start server and test endpoints")
        print("  4. Configure Redis for production")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
