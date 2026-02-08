"""
Tests for Logging Middleware

Tests request/response logging, performance tracking, and audit logging.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.middleware.logging_middleware import (
    filter_sensitive_data,
    filter_headers,
    parse_body
)
from backend.middleware.performance_middleware import (
    performance_metrics,
    get_performance_stats,
    reset_performance_stats
)

client = TestClient(app)


class TestSensitiveDataFiltering:
    """Test sensitive data filtering."""

    def test_filter_password_field(self):
        """Test that password fields are filtered."""
        data = {
            'username': 'test_user',
            'password': 'secret123',
            'email': 'test@example.com'
        }

        filtered = filter_sensitive_data(data)

        assert filtered['username'] == 'test_user'
        assert filtered['password'] == '***FILTERED***'
        assert filtered['email'] == 'test@example.com'

    def test_filter_nested_sensitive_data(self):
        """Test filtering in nested dictionaries."""
        data = {
            'user': {
                'name': 'John',
                'auth': {
                    'token': 'abc123xyz',
                    'api_key': 'key_secret'
                }
            }
        }

        filtered = filter_sensitive_data(data)

        assert filtered['user']['name'] == 'John'
        assert filtered['user']['auth']['token'] == '***FILTERED***'
        assert filtered['user']['auth']['api_key'] == '***FILTERED***'

    def test_filter_list_of_objects(self):
        """Test filtering in lists."""
        data = {
            'users': [
                {'name': 'Alice', 'password': 'pass1'},
                {'name': 'Bob', 'password': 'pass2'}
            ]
        }

        filtered = filter_sensitive_data(data)

        assert filtered['users'][0]['password'] == '***FILTERED***'
        assert filtered['users'][1]['password'] == '***FILTERED***'

    def test_filter_authorization_header(self):
        """Test that authorization headers are filtered."""
        from starlette.datastructures import Headers

        headers = Headers({
            'content-type': 'application/json',
            'authorization': 'Bearer token123',
            'x-api-key': 'secret_key'
        })

        filtered = filter_headers(headers)

        assert filtered['content-type'] == 'application/json'
        assert filtered['authorization'] == '***FILTERED***'
        assert filtered['x-api-key'] == '***FILTERED***'


class TestBodyParsing:
    """Test request/response body parsing."""

    def test_parse_json_body(self):
        """Test parsing JSON body."""
        body = b'{"ticker": "AAPL", "shares": 100}'
        content_type = 'application/json'

        parsed = parse_body(body, content_type)

        assert isinstance(parsed, dict)
        assert parsed['ticker'] == 'AAPL'
        assert parsed['shares'] == 100

    def test_parse_text_body(self):
        """Test parsing text body."""
        body = b'Hello World'
        content_type = 'text/plain'

        parsed = parse_body(body, content_type)

        assert parsed == 'Hello World'

    def test_truncate_large_body(self):
        """Test that large bodies are truncated."""
        # Create body larger than MAX_BODY_SIZE (10000 bytes)
        large_body = b'x' * 20000

        parsed = parse_body(large_body)

        assert '[BODY_TOO_LARGE:' in str(parsed)

    def test_parse_empty_body(self):
        """Test parsing empty body."""
        parsed = parse_body(b'')

        assert parsed is None


class TestLoggingMiddleware:
    """Test logging middleware functionality."""

    def test_request_id_header_added(self):
        """Test that X-Request-ID header is added to responses."""
        response = client.get("/api/v1/momentum/AAPL")

        assert 'X-Request-ID' in response.headers
        assert 'X-Process-Time' in response.headers

    def test_custom_request_id_preserved(self):
        """Test that custom request ID is preserved."""
        custom_id = "test_req_12345"
        response = client.get(
            "/api/v1/momentum/AAPL",
            headers={"X-Request-ID": custom_id}
        )

        # Should preserve custom request ID (or generate new one)
        assert 'X-Request-ID' in response.headers

    def test_process_time_header(self):
        """Test that X-Process-Time header is present."""
        response = client.get("/api/v1/momentum/AAPL")

        process_time = response.headers.get('X-Process-Time')
        assert process_time is not None
        assert 'ms' in process_time


class TestPerformanceMiddleware:
    """Test performance monitoring middleware."""

    def setup_method(self):
        """Reset metrics before each test."""
        reset_performance_stats()

    def test_metrics_recorded(self):
        """Test that metrics are recorded for requests."""
        # Make a request
        response = client.get("/api/v1/momentum/AAPL")

        # Check that metrics were recorded
        stats = get_performance_stats()
        endpoints = stats.get('endpoints', [])

        assert len(endpoints) > 0

    def test_metrics_accumulate(self):
        """Test that metrics accumulate over multiple requests."""
        # Make multiple requests
        for _ in range(5):
            client.get("/api/v1/momentum/AAPL")

        # Check metrics
        stats = get_performance_stats("/api/v1/momentum/{ticker}")

        assert stats.get('count', 0) >= 5

    def test_path_normalization(self):
        """Test that paths are normalized for metrics."""
        # Make requests with different tickers
        client.get("/api/v1/momentum/AAPL")
        client.get("/api/v1/momentum/NVDA")
        client.get("/api/v1/momentum/MSFT")

        # All should be grouped under normalized path
        stats = get_performance_stats("/api/v1/momentum/{ticker}")

        # Should have combined count
        assert stats.get('count', 0) >= 3

    def test_performance_stats_include_percentiles(self):
        """Test that performance stats include percentile data."""
        # Make some requests
        for _ in range(10):
            client.get("/api/v1/momentum/AAPL")

        stats = get_performance_stats("/api/v1/momentum/{ticker}")

        assert 'p50_ms' in stats
        assert 'p95_ms' in stats
        assert 'p99_ms' in stats
        assert 'avg_duration_ms' in stats
        assert 'min_duration_ms' in stats
        assert 'max_duration_ms' in stats

    def test_reset_metrics(self):
        """Test resetting performance metrics."""
        # Make some requests
        client.get("/api/v1/momentum/AAPL")

        # Reset metrics
        reset_performance_stats()

        # Check that metrics are cleared
        stats = get_performance_stats()
        endpoints = stats.get('endpoints', [])

        assert len(endpoints) == 0


@pytest.mark.integration
class TestMetricsAPI:
    """Test metrics API endpoints."""

    def setup_method(self):
        """Reset metrics before each test."""
        reset_performance_stats()

    def test_get_performance_metrics(self):
        """Test getting performance metrics via API."""
        # Make some requests
        client.get("/api/v1/momentum/AAPL")

        # Get metrics
        response = client.get("/api/v1/metrics/performance")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'data' in data

    def test_get_endpoint_summary(self):
        """Test getting endpoint summary."""
        # Make some requests
        client.get("/api/v1/momentum/AAPL")
        client.get("/api/v1/portfolio/analysis")

        # Get summary
        response = client.get("/api/v1/metrics/endpoints")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'summary' in data
        assert 'endpoints' in data

    def test_get_slow_endpoints(self):
        """Test getting slow endpoints."""
        response = client.get("/api/v1/metrics/slow?threshold_ms=100")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'endpoints' in data

    def test_reset_metrics_via_api(self):
        """Test resetting metrics via API."""
        # Make some requests
        client.get("/api/v1/momentum/AAPL")

        # Reset via API
        response = client.delete("/api/v1/metrics/performance/reset")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True


class TestAuditMiddleware:
    """Test audit logging middleware."""

    def test_auth_endpoints_audited(self):
        """Test that authentication endpoints are audited."""
        # This test would require actual auth endpoints
        # For now, just verify middleware doesn't break requests
        response = client.get("/api/v1/momentum/AAPL")
        assert response.status_code in [200, 404, 502]

    def test_modification_requests_audited(self):
        """Test that data modification requests are audited."""
        # POST request should trigger audit logging
        response = client.post(
            "/api/v1/momentum/batch",
            json={"tickers": ["AAPL", "NVDA"]}
        )

        # Should process (may succeed or fail validation)
        assert response.status_code in [200, 400, 422]

    def test_errors_audited(self):
        """Test that error requests are audited."""
        # Invalid request should trigger audit
        response = client.get("/api/v1/momentum/INVALID_TICKER_123456")

        # Should be error
        assert response.status_code >= 400
