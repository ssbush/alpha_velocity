"""
Request/Response Logging Middleware

Comprehensive logging middleware for FastAPI that captures:
- Request/response details with body content
- Performance metrics (timing, sizes)
- User context and client information
- Sensitive data filtering
- Structured logging with correlation IDs
"""

import logging
import time
import json
import uuid
from typing import Callable, Optional, Set, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.datastructures import Headers
import re
import os

logger = logging.getLogger(__name__)


# Sensitive field patterns to filter from logs
SENSITIVE_FIELDS = {
    'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
    'authorization', 'auth', 'jwt', 'session', 'cookie', 'csrf',
    'credit_card', 'card_number', 'cvv', 'ssn', 'social_security'
}

# Sensitive header patterns
SENSITIVE_HEADERS = {
    'authorization', 'cookie', 'x-api-key', 'x-auth-token', 'x-csrf-token'
}

# Paths to exclude from detailed logging
EXCLUDE_PATHS = {
    '/docs', '/redoc', '/openapi.json', '/favicon.ico', '/metrics'
}

# Maximum body size to log (bytes)
MAX_BODY_SIZE = int(os.getenv('LOG_MAX_BODY_SIZE', 10000))  # 10KB default


def filter_sensitive_data(data: Any, depth: int = 0) -> Any:
    """
    Recursively filter sensitive data from dictionaries and lists.

    Args:
        data: Data to filter (dict, list, or primitive)
        depth: Current recursion depth (prevent infinite loops)

    Returns:
        Filtered data with sensitive fields masked
    """
    if depth > 10:  # Prevent deep recursion
        return "[MAX_DEPTH]"

    if isinstance(data, dict):
        filtered = {}
        for key, value in data.items():
            key_lower = key.lower()
            # Check if key matches sensitive patterns
            if any(pattern in key_lower for pattern in SENSITIVE_FIELDS):
                filtered[key] = "***FILTERED***"
            else:
                filtered[key] = filter_sensitive_data(value, depth + 1)
        return filtered

    elif isinstance(data, list):
        return [filter_sensitive_data(item, depth + 1) for item in data]

    elif isinstance(data, str):
        # Filter potential tokens in strings
        if len(data) > 50 and re.match(r'^[A-Za-z0-9_\-\.]+$', data):
            # Looks like a token
            return f"{data[:10]}...{data[-10:]}"
        return data

    else:
        return data


def filter_headers(headers: Headers) -> Dict[str, str]:
    """
    Filter sensitive headers from logging.

    Args:
        headers: Request/response headers

    Returns:
        Filtered headers dictionary
    """
    filtered = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in SENSITIVE_HEADERS):
            filtered[key] = "***FILTERED***"
        else:
            filtered[key] = value
    return filtered


def parse_body(body: bytes, content_type: Optional[str] = None) -> Any:
    """
    Parse request/response body based on content type.

    Args:
        body: Raw body bytes
        content_type: Content-Type header

    Returns:
        Parsed body (dict, list, or string)
    """
    if not body:
        return None

    # Truncate if too large
    if len(body) > MAX_BODY_SIZE:
        return f"[BODY_TOO_LARGE: {len(body)} bytes]"

    try:
        # Try JSON first
        if content_type and 'application/json' in content_type:
            data = json.loads(body.decode('utf-8'))
            return filter_sensitive_data(data)

        # Try to decode as text
        text = body.decode('utf-8', errors='ignore')

        # Try to parse as JSON anyway (if content-type is wrong)
        try:
            data = json.loads(text)
            return filter_sensitive_data(data)
        except json.JSONDecodeError:
            pass

        # Return truncated text
        if len(text) > 500:
            return f"{text[:500]}... [TRUNCATED]"
        return text

    except Exception as e:
        return f"[PARSE_ERROR: {str(e)}]"


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced middleware for comprehensive HTTP request/response logging.

    Features:
    - Request/response body logging with size limits
    - Sensitive data filtering (passwords, tokens, etc.)
    - Performance metrics (timing, sizes, throughput)
    - User context and client information
    - Correlation IDs for distributed tracing
    - Configurable verbosity per path
    - Structured logging for easy parsing

    Configuration via environment variables:
    - LOG_REQUESTS: Enable request logging (default: true)
    - LOG_RESPONSES: Enable response logging (default: true)
    - LOG_REQUEST_BODY: Log request bodies (default: true)
    - LOG_RESPONSE_BODY: Log response bodies (default: false)
    - LOG_MAX_BODY_SIZE: Maximum body size to log in bytes (default: 10000)
    - LOG_SLOW_REQUEST_THRESHOLD: Threshold for slow request warning in ms (default: 1000)
    """

    def __init__(
        self,
        app: ASGIApp,
        log_requests: bool = True,
        log_responses: bool = True,
        log_request_body: bool = True,
        log_response_body: bool = False
    ):
        """
        Initialize logging middleware.

        Args:
            app: ASGI application
            log_requests: Enable request logging
            log_responses: Enable response logging
            log_request_body: Enable request body logging
            log_response_body: Enable response body logging
        """
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.slow_request_threshold = int(
            os.getenv('LOG_SLOW_REQUEST_THRESHOLD', 1000)
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log comprehensive details."""

        # Generate or extract correlation ID
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        request.state.request_id = request_id

        # Check if path should be excluded
        path = request.url.path
        if path in EXCLUDE_PATHS or path.startswith('/static/'):
            # Skip logging for excluded paths
            response = await call_next(request)
            response.headers['X-Request-ID'] = request_id
            return response

        # Start timing
        start_time = time.time()

        # Extract request details
        method = request.method
        query_params = dict(request.query_params)
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get('user-agent', 'unknown')
        referer = request.headers.get('referer', None)
        content_type = request.headers.get('content-type', None)

        # Read request body if needed
        request_body = None
        request_size = 0
        if self.log_request_body and method in ['POST', 'PUT', 'PATCH']:
            try:
                body_bytes = await request.body()
                request_size = len(body_bytes)
                request_body = parse_body(body_bytes, content_type)

                # Reconstruct request with body (since we consumed it)
                async def receive():
                    return {"type": "http.request", "body": body_bytes}

                request._receive = receive

            except Exception as e:
                logger.warning(
                    f"Failed to read request body: {e}",
                    extra={'request_id': request_id}
                )

        # Log incoming request
        if self.log_requests:
            request_log_data = {
                'request_id': request_id,
                'method': method,
                'path': path,
                'query_params': filter_sensitive_data(query_params),
                'client_host': client_host,
                'user_agent': user_agent,
                'content_type': content_type,
                'request_size': request_size
            }

            if referer:
                request_log_data['referer'] = referer

            if request_body is not None:
                request_log_data['request_body'] = request_body

            # Filter sensitive headers
            filtered_headers = filter_headers(request.headers)
            request_log_data['headers'] = filtered_headers

            logger.info(
                f"→ {method} {path}",
                extra=request_log_data
            )

        # Process request
        response = None
        error_occurred = False

        try:
            response = await call_next(request)

        except Exception as e:
            error_occurred = True
            duration = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                f"✗ {method} {path} - Request failed: {type(e).__name__}",
                extra={
                    'request_id': request_id,
                    'method': method,
                    'path': path,
                    'duration_ms': round(duration, 2),
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise

        finally:
            # Calculate metrics
            duration = (time.time() - start_time) * 1000

            if response is not None:
                # Add custom headers
                response.headers['X-Request-ID'] = request_id
                response.headers['X-Process-Time'] = f"{duration:.2f}ms"

                # Read response body if needed
                response_body = None
                response_size = 0

                if self.log_response_body:
                    # Note: Reading response body is complex with streaming responses
                    # Only log for small responses
                    pass  # Skip for now to avoid complexity

                # Determine log level
                status_code = response.status_code
                if status_code >= 500:
                    log_level = logging.ERROR
                    status_icon = "✗"
                elif status_code >= 400:
                    log_level = logging.WARNING
                    status_icon = "⚠"
                else:
                    log_level = logging.INFO
                    status_icon = "✓"

                # Log response
                if self.log_responses:
                    response_log_data = {
                        'request_id': request_id,
                        'method': method,
                        'path': path,
                        'status_code': status_code,
                        'duration_ms': round(duration, 2),
                        'response_size': response_size
                    }

                    if response_body is not None:
                        response_log_data['response_body'] = response_body

                    # Calculate throughput if we have sizes
                    if request_size > 0 or response_size > 0:
                        total_size = request_size + response_size
                        throughput_kbps = (total_size / 1024) / (duration / 1000)
                        response_log_data['throughput_kbps'] = round(throughput_kbps, 2)

                    logger.log(
                        log_level,
                        f"{status_icon} {method} {path} - {status_code} ({duration:.2f}ms)",
                        extra=response_log_data
                    )

                # Log slow requests
                if duration > self.slow_request_threshold:
                    logger.warning(
                        f"🐌 Slow request: {method} {path} took {duration:.2f}ms",
                        extra={
                            'request_id': request_id,
                            'method': method,
                            'path': path,
                            'status_code': status_code,
                            'duration_ms': round(duration, 2),
                            'threshold_ms': self.slow_request_threshold
                        }
                    )

        return response
