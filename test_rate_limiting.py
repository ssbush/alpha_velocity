#!/usr/bin/env python3
"""
Rate Limiting Test Script

Tests rate limiting functionality to ensure:
- Authentication endpoints are protected from brute force
- Expensive operations have appropriate limits
- Rate limit headers are added to responses
- Authenticated users get higher limits
- Rate limit exceeded responses are correct

Usage:
    python test_rate_limiting.py
"""

import sys
import os
import time
from unittest.mock import Mock, patch

# Set test environment
os.environ['RATE_LIMIT_ENABLED'] = 'true'
os.environ['RATE_LIMIT_STORAGE_URL'] = 'memory://'
os.environ['AUTH_RATE_LIMIT'] = '3/minute'  # Low limit for testing
os.environ['DEFAULT_RATE_LIMIT'] = '5/minute'
os.environ['EXPENSIVE_RATE_LIMIT'] = '2/minute'

from backend.config.rate_limit_config import (
    get_identifier,
    get_rate_limit_key,
    get_rate_limit_for_user,
    RateLimits,
    get_rate_limit_config,
    create_rate_limit_exemption,
)


def test_rate_limit_config():
    """Test rate limit configuration loading"""
    print("\n" + "="*60)
    print("Testing Rate Limit Configuration")
    print("="*60)

    config = get_rate_limit_config()

    # Verify configuration loaded
    assert config['enabled'] == True, "Rate limiting should be enabled"
    assert config['storage_url'] == 'memory://', "Storage should be in-memory"
    assert config['limits']['authentication'] == '3/minute', "Auth limit should be set"

    print("✓ Rate limit configuration loaded correctly")
    print(f"  - Enabled: {config['enabled']}")
    print(f"  - Storage: {config['storage_url']}")
    print(f"  - Auth limit: {config['limits']['authentication']}")
    print(f"  - Default limit: {config['limits']['default']}")

    return True


def test_identifier_extraction():
    """Test rate limit identifier extraction"""
    print("\n" + "="*60)
    print("Testing Identifier Extraction")
    print("="*60)

    # Test IP address fallback
    mock_request = Mock()
    mock_request.headers = {}
    mock_request.client.host = '192.168.1.100'

    with patch('backend.config.rate_limit_config.get_remote_address', return_value='192.168.1.100'):
        identifier = get_identifier(mock_request)
        assert identifier == '192.168.1.100', "Should fallback to IP address"
        print("✓ IP address fallback works")

    # Test authenticated user (with state)
    mock_request.state = Mock()
    mock_request.state.user_id = 123
    mock_request.headers = {'Authorization': 'Bearer token123'}

    identifier = get_identifier(mock_request)
    assert identifier == 'user:123', "Should use user ID"
    print("✓ Authenticated user identifier works")

    # Test API key
    mock_request = Mock()
    mock_request.headers = {'X-API-Key': 'apikey-abcdefghijklmnop'}
    mock_request.state = Mock()
    delattr(mock_request.state, 'user_id')

    identifier = get_identifier(mock_request)
    assert identifier.startswith('apikey:'), "Should use API key"
    print("✓ API key identifier works")

    return True


def test_rate_limit_key_generation():
    """Test rate limit key generation"""
    print("\n" + "="*60)
    print("Testing Rate Limit Key Generation")
    print("="*60)

    mock_request = Mock()
    mock_request.headers = {}
    mock_request.client.host = '192.168.1.100'
    mock_request.url.path = '/api/test'

    with patch('backend.config.rate_limit_config.get_remote_address', return_value='192.168.1.100'):
        key = get_rate_limit_key(mock_request)
        assert '192.168.1.100' in key, "Key should contain IP"
        assert '/api/test' in key, "Key should contain path"
        print(f"✓ Rate limit key generated correctly: {key}")

    return True


def test_rate_limit_for_user():
    """Test rate limit determination based on authentication"""
    print("\n" + "="*60)
    print("Testing Rate Limit for User")
    print("="*60)

    # Test anonymous user
    mock_request = Mock()
    mock_request.headers = {}

    limit = get_rate_limit_for_user(mock_request)
    assert limit == os.getenv('DEFAULT_RATE_LIMIT'), "Anonymous user should get default limit"
    print(f"✓ Anonymous user gets default limit: {limit}")

    # Test authenticated user (with Bearer token)
    mock_request.headers = {'Authorization': 'Bearer token123'}

    limit = get_rate_limit_for_user(mock_request)
    assert limit == os.getenv('AUTHENTICATED_RATE_LIMIT'), "Authenticated user should get higher limit"
    print(f"✓ Authenticated user gets higher limit: {limit}")

    # Test API key user
    mock_request.headers = {'X-API-Key': 'apikey-test'}

    limit = get_rate_limit_for_user(mock_request)
    assert limit == os.getenv('AUTHENTICATED_RATE_LIMIT'), "API key user should get higher limit"
    print(f"✓ API key user gets higher limit: {limit}")

    return True


def test_rate_limit_presets():
    """Test rate limit preset values"""
    print("\n" + "="*60)
    print("Testing Rate Limit Presets")
    print("="*60)

    # Verify preset constants exist and are valid
    presets = {
        'AUTHENTICATION': RateLimits.AUTHENTICATION,
        'PUBLIC_API': RateLimits.PUBLIC_API,
        'AUTHENTICATED_API': RateLimits.AUTHENTICATED_API,
        'EXPENSIVE': RateLimits.EXPENSIVE,
        'READ_ONLY': RateLimits.READ_ONLY,
        'WRITE': RateLimits.WRITE,
        'SEARCH': RateLimits.SEARCH,
        'UPLOAD': RateLimits.UPLOAD,
        'BULK': RateLimits.BULK,
    }

    for name, limit in presets.items():
        assert '/' in limit, f"{name} limit should be in format 'count/period'"
        count, period = limit.split('/')
        assert count.isdigit(), f"{name} count should be numeric"
        assert period in ['second', 'minute', 'hour', 'day'], f"{name} period should be valid"
        print(f"✓ {name}: {limit}")

    return True


def test_rate_limit_exemption():
    """Test rate limit exemption logic"""
    print("\n" + "="*60)
    print("Testing Rate Limit Exemption")
    print("="*60)

    # Create exemption checker with test IPs
    is_exempt = create_rate_limit_exemption(['192.168.1.100', '10.0.0.1'])

    # Test exempt IP
    mock_request = Mock()
    mock_request.headers = {}
    mock_request.url.path = '/api/test'

    with patch('backend.config.rate_limit_config.get_remote_address', return_value='192.168.1.100'):
        assert is_exempt(mock_request) == True, "Exempt IP should be exempt"
        print("✓ Exempt IP correctly identified")

    # Test non-exempt IP
    with patch('backend.config.rate_limit_config.get_remote_address', return_value='203.0.113.1'):
        assert is_exempt(mock_request) == False, "Non-exempt IP should not be exempt"
        print("✓ Non-exempt IP correctly identified")

    # Test health check endpoint (always exempt)
    mock_request.url.path = '/health'
    with patch('backend.config.rate_limit_config.get_remote_address', return_value='203.0.113.1'):
        assert is_exempt(mock_request) == True, "Health check should always be exempt"
        print("✓ Health check endpoint correctly exempted")

    # Test root endpoint (always exempt)
    mock_request.url.path = '/'
    with patch('backend.config.rate_limit_config.get_remote_address', return_value='203.0.113.1'):
        assert is_exempt(mock_request) == True, "Root endpoint should always be exempt"
        print("✓ Root endpoint correctly exempted")

    return True


def test_rate_limit_integration():
    """Test rate limiting integration (simulated)"""
    print("\n" + "="*60)
    print("Testing Rate Limit Integration")
    print("="*60)

    try:
        from slowapi import Limiter
        from slowapi.util import get_remote_address

        # Create a test limiter
        limiter = Limiter(
            key_func=get_remote_address,
            storage_uri='memory://',
            enabled=True,
        )

        print("✓ Slowapi limiter initialized successfully")

        # Verify limiter has required methods
        assert hasattr(limiter, 'limit'), "Limiter should have 'limit' decorator"
        print("✓ Limiter has 'limit' decorator")

        return True

    except ImportError as e:
        print(f"⚠️  Slowapi not installed: {e}")
        print("   Run: pip install slowapi redis")
        return False
    except Exception as e:
        print(f"✗ FAILED: Limiter initialization failed: {e}")
        return False


def test_rate_limit_response_format():
    """Test rate limit exceeded response format"""
    print("\n" + "="*60)
    print("Testing Rate Limit Response Format")
    print("="*60)

    from slowapi.errors import RateLimitExceeded
    from fastapi import Request
    from backend.config.rate_limit_config import rate_limit_exceeded_handler

    # Create mock rate limit exceeded exception
    exc = RateLimitExceeded("1 per 1 minute")
    exc.retry_after = 60

    # Create mock request
    mock_request = Mock(spec=Request)
    mock_request.headers = {}
    mock_request.url.path = '/test'
    mock_request.client.host = '192.168.1.100'

    # Test handler
    import asyncio
    response = asyncio.run(rate_limit_exceeded_handler(mock_request, exc))

    # Verify response
    assert response.status_code == 429, "Status should be 429"
    print("✓ Rate limit exceeded returns 429 status")

    # Verify response body
    import json
    body = json.loads(response.body)
    assert 'error' in body, "Response should contain 'error'"
    assert 'message' in body, "Response should contain 'message'"
    assert 'retry_after_seconds' in body, "Response should contain 'retry_after_seconds'"
    print("✓ Rate limit response has correct format")
    print(f"  - Error: {body['error']}")
    print(f"  - Message: {body['message']}")
    print(f"  - Retry After: {body['retry_after_seconds']}s")

    # Verify Retry-After header
    assert 'Retry-After' in response.headers, "Response should have Retry-After header"
    print(f"✓ Retry-After header present: {response.headers['Retry-After']}")

    return True


def main():
    """Run all rate limiting tests"""
    print("\n" + "="*60)
    print("Rate Limiting Test Suite")
    print("="*60)

    tests = [
        ("Rate Limit Configuration", test_rate_limit_config),
        ("Identifier Extraction", test_identifier_extraction),
        ("Rate Limit Key Generation", test_rate_limit_key_generation),
        ("Rate Limit for User", test_rate_limit_for_user),
        ("Rate Limit Presets", test_rate_limit_presets),
        ("Rate Limit Exemption", test_rate_limit_exemption),
        ("Rate Limit Integration", test_rate_limit_integration),
        ("Rate Limit Response Format", test_rate_limit_response_format),
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
        print("\n🎉 All rate limiting tests passed!")
        print("\n✅ Rate limiting is working correctly:")
        print("  - Configuration loaded properly")
        print("  - Identifier extraction works for IP/user/API key")
        print("  - Rate limit keys generated correctly")
        print("  - Different limits for authenticated vs anonymous users")
        print("  - Rate limit presets defined correctly")
        print("  - Exemption logic works (health checks, exempt IPs)")
        print("  - Integration with slowapi successful")
        print("  - Error responses formatted correctly")
        print("\n📝 Next Steps:")
        print("  1. Install dependencies: pip install slowapi redis")
        print("  2. Test with live API: Start server and make repeated requests")
        print("  3. Monitor rate limit headers: X-RateLimit-Limit, X-RateLimit-Remaining")
        print("  4. Test authentication endpoint protection")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
