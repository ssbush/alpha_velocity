## Logging Middleware Documentation

## Overview

AlphaVelocity implements a comprehensive multi-layered logging system that provides:
- **Request/Response Logging** - Detailed logging of all API requests and responses
- **Performance Monitoring** - Real-time performance metrics and statistics
- **Audit Logging** - Security-relevant event tracking for compliance
- **Sensitive Data Filtering** - Automatic masking of passwords, tokens, and secrets

## Table of Contents

- [Architecture](#architecture)
- [Middleware Layers](#middleware-layers)
- [Sensitive Data Filtering](#sensitive-data-filtering)
- [Performance Metrics](#performance-metrics)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [API Endpoints](#api-endpoints)
- [Best Practices](#best-practices)

---

## Architecture

### Middleware Stack (Execution Order)

```
Request Flow:
┌─────────────────────────────────────────┐
│  1. PerformanceMiddleware               │  ← Outermost (measures total time)
│     ↓                                   │
│  2. AuditMiddleware                     │  ← Security event logging
│     ↓                                   │
│  3. LoggingMiddleware                   │  ← Detailed request/response logging
│     ↓                                   │
│  4. ExceptionHandlers                   │  ← Error handling
│     ↓                                   │
│  5. RateLimitMiddleware                 │  ← Rate limiting
│     ↓                                   │
│  6. Application Logic                   │  ← FastAPI routes
└─────────────────────────────────────────┘
```

**Note:** Middleware is executed in reverse order of addition (LIFO - Last In, First Out).

---

## Middleware Layers

### 1. LoggingMiddleware

Comprehensive request/response logging with body capture and sensitive data filtering.

**Features:**
- Request details (method, path, headers, query params, body)
- Response details (status code, headers, body - optional)
- Request ID correlation for distributed tracing
- Sensitive data filtering (passwords, tokens, etc.)
- Performance timing
- Client information (IP, user agent, referer)
- Configurable verbosity

**Log Format:**
```
INFO: → POST /api/v1/momentum/batch
{
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "method": "POST",
  "path": "/api/v1/momentum/batch",
  "query_params": {},
  "client_host": "127.0.0.1",
  "user_agent": "python-requests/2.31.0",
  "content_type": "application/json",
  "request_size": 45,
  "request_body": {
    "tickers": ["AAPL", "NVDA"]
  },
  "headers": {
    "content-type": "application/json",
    "authorization": "***FILTERED***"
  }
}

INFO: ✓ POST /api/v1/momentum/batch - 200 (234.56ms)
{
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "method": "POST",
  "path": "/api/v1/momentum/batch",
  "status_code": 200,
  "duration_ms": 234.56
}
```

**Configuration:**
```python
# Environment variables
LOG_REQUESTS=true                  # Enable request logging
LOG_RESPONSES=true                 # Enable response logging
LOG_REQUEST_BODY=true              # Log request bodies
LOG_RESPONSE_BODY=false            # Log response bodies
LOG_MAX_BODY_SIZE=10000           # Max body size (bytes)
LOG_SLOW_REQUEST_THRESHOLD=1000   # Slow request threshold (ms)
```

**Code Configuration:**
```python
app.add_middleware(
    LoggingMiddleware,
    log_requests=True,
    log_responses=True,
    log_request_body=True,
    log_response_body=False
)
```

---

### 2. PerformanceMiddleware

Tracks and aggregates performance metrics for all endpoints.

**Features:**
- Request count per endpoint
- Response time statistics (avg, min, max, percentiles)
- Status code distribution
- Error rate tracking
- Path normalization (groups similar paths)
- Thread-safe metrics collection

**Metrics Collected:**
- `count` - Total requests
- `avg_duration_ms` - Average response time
- `min_duration_ms` - Minimum response time
- `max_duration_ms` - Maximum response time
- `p50_ms` - 50th percentile (median)
- `p95_ms` - 95th percentile
- `p99_ms` - 99th percentile
- `status_codes` - Distribution of status codes
- `error_count` - Number of 5xx errors
- `error_rate_percent` - Percentage of errors

**Example Metrics:**
```json
{
  "endpoint": "/api/v1/momentum/{ticker}",
  "count": 1543,
  "avg_duration_ms": 234.56,
  "min_duration_ms": 45.23,
  "max_duration_ms": 1234.56,
  "p50_ms": 198.45,
  "p95_ms": 567.89,
  "p99_ms": 987.65,
  "status_codes": {
    "200": 1489,
    "400": 32,
    "404": 15,
    "500": 7
  },
  "error_count": 7,
  "error_rate_percent": 0.45,
  "sample_size": 1000
}
```

**Path Normalization:**
```
/api/v1/momentum/AAPL   → /api/v1/momentum/{ticker}
/api/v1/momentum/NVDA   → /api/v1/momentum/{ticker}
/api/v1/portfolio/123   → /api/v1/portfolio/{id}
```

**Configuration:**
```python
app.add_middleware(
    PerformanceMiddleware,
    enable_logging=True,      # Enable slow request logging
    log_threshold_ms=5000.0   # Threshold for very slow requests
)
```

---

### 3. AuditMiddleware

Records security-relevant events for compliance and forensics.

**Features:**
- Authentication attempts
- Authorization failures
- Data modifications
- Admin access
- Error events
- User context (IP, user agent, user ID)
- Event classification

**Audited Events:**
- Authentication (login, register, logout)
- Authorization failures (401, 403)
- Data modification (POST, PUT, PATCH, DELETE)
- Sensitive resource access (admin endpoints, user data)
- Server errors (500+)

**Log Format:**
```json
{
  "timestamp": "2024-01-25T12:34:56.789Z",
  "event_type": "authentication_attempt",
  "method": "POST",
  "path": "/api/v1/auth/login",
  "status_code": 200,
  "request_id": "abc123",
  "user_id": null,
  "username": null,
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0..."
}
```

**Event Types:**
- `authentication_attempt`
- `user_registration`
- `logout`
- `authentication_failure`
- `authorization_failure`
- `resource_creation`
- `resource_update`
- `resource_deletion`
- `admin_access`
- `server_error`
- `client_error`

**Configuration:**
```python
app.add_middleware(
    AuditMiddleware,
    enable_audit=True,        # Enable audit logging
    log_all_requests=False    # Log all requests (high-security mode)
)
```

---

## Sensitive Data Filtering

### Automatic Filtering

The logging system automatically filters sensitive data to prevent accidental exposure in logs.

**Filtered Fields:**
```python
SENSITIVE_FIELDS = {
    'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
    'authorization', 'auth', 'jwt', 'session', 'cookie', 'csrf',
    'credit_card', 'card_number', 'cvv', 'ssn', 'social_security'
}
```

**Filtered Headers:**
```python
SENSITIVE_HEADERS = {
    'authorization', 'cookie', 'x-api-key', 'x-auth-token', 'x-csrf-token'
}
```

### Examples

**Request Body Filtering:**
```python
# Original
{
  "username": "john_doe",
  "password": "secret123",
  "email": "john@example.com"
}

# Filtered
{
  "username": "john_doe",
  "password": "***FILTERED***",
  "email": "john@example.com"
}
```

**Nested Object Filtering:**
```python
# Original
{
  "user": {
    "name": "John",
    "auth": {
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "api_key": "sk_live_abc123xyz"
    }
  }
}

# Filtered
{
  "user": {
    "name": "John",
    "auth": {
      "token": "***FILTERED***",
      "api_key": "***FILTERED***"
    }
  }
}
```

**Header Filtering:**
```python
# Original Headers
Authorization: Bearer token123
X-API-Key: secret_key
Content-Type: application/json

# Filtered
{
  "authorization": "***FILTERED***",
  "x-api-key": "***FILTERED***",
  "content-type": "application/json"
}
```

---

## Performance Metrics

### Accessing Metrics

#### Via API

```bash
# Get all performance metrics
GET /api/v1/metrics/performance

# Get specific endpoint metrics
GET /api/v1/metrics/performance?endpoint=/api/v1/momentum/{ticker}

# Get endpoint summary
GET /api/v1/metrics/endpoints

# Get slow endpoints
GET /api/v1/metrics/slow?threshold_ms=500

# Reset metrics
DELETE /api/v1/metrics/performance/reset
```

#### Via Python

```python
from backend.middleware.performance_middleware import (
    get_performance_stats,
    reset_performance_stats
)

# Get all stats
all_stats = get_performance_stats()

# Get specific endpoint
momentum_stats = get_performance_stats("/api/v1/momentum/{ticker}")

# Reset metrics
reset_performance_stats()
```

### Metrics Response Format

```json
{
  "success": true,
  "data": {
    "endpoints": [
      {
        "endpoint": "/api/v1/momentum/{ticker}",
        "count": 1543,
        "avg_duration_ms": 234.56,
        "min_duration_ms": 45.23,
        "max_duration_ms": 1234.56,
        "p50_ms": 198.45,
        "p95_ms": 567.89,
        "p99_ms": 987.65,
        "status_codes": {
          "200": 1489,
          "400": 32,
          "404": 15,
          "500": 7
        },
        "error_count": 7,
        "error_rate_percent": 0.45,
        "sample_size": 1000
      }
    ],
    "total_endpoints": 15
  }
}
```

---

## Configuration

### Environment Variables

```bash
# Logging Configuration
LOG_LEVEL=INFO                      # Log level (DEBUG, INFO, WARNING, ERROR)
LOG_DIR=logs                        # Log directory
JSON_LOGS=false                     # JSON format for logs

# Request/Response Logging
LOG_REQUESTS=true                   # Enable request logging
LOG_RESPONSES=true                  # Enable response logging
LOG_REQUEST_BODY=true               # Log request bodies
LOG_RESPONSE_BODY=false             # Log response bodies
LOG_MAX_BODY_SIZE=10000            # Max body size to log (bytes)
LOG_SLOW_REQUEST_THRESHOLD=1000    # Slow request threshold (ms)

# Performance Monitoring
PERFORMANCE_TRACKING=true           # Enable performance tracking
PERFORMANCE_LOG_THRESHOLD_MS=5000  # Very slow request threshold

# Audit Logging
AUDIT_LOGGING=true                  # Enable audit logging
AUDIT_ALL_REQUESTS=false            # Log all requests (high-security)
```

### Python Configuration

```python
from backend.middleware.logging_middleware import LoggingMiddleware
from backend.middleware.performance_middleware import PerformanceMiddleware
from backend.middleware.audit_middleware import AuditMiddleware

# Configure middleware
app.add_middleware(
    PerformanceMiddleware,
    enable_logging=True,
    log_threshold_ms=5000.0
)

app.add_middleware(
    AuditMiddleware,
    enable_audit=True,
    log_all_requests=False
)

app.add_middleware(
    LoggingMiddleware,
    log_requests=True,
    log_responses=True,
    log_request_body=True,
    log_response_body=False
)
```

---

## Usage Examples

### Example 1: Viewing Request Logs

```bash
# Tail application logs
tail -f logs/alphavelocity.log

# Filter for specific request
tail -f logs/alphavelocity.log | grep "req_abc123"

# Filter for errors
tail -f logs/alphavelocity.log | grep "ERROR"

# Filter for slow requests
tail -f logs/alphavelocity.log | grep "Slow request"
```

### Example 2: Monitoring Performance

```python
import requests

# Get performance metrics
response = requests.get("http://localhost:8000/api/v1/metrics/performance")
metrics = response.json()

# Find slowest endpoints
endpoints = metrics['data']['endpoints']
slowest = sorted(endpoints, key=lambda x: x['avg_duration_ms'], reverse=True)

print(f"Slowest endpoint: {slowest[0]['endpoint']}")
print(f"Average time: {slowest[0]['avg_duration_ms']}ms")
```

### Example 3: Tracking Request with ID

```bash
# Make request with custom ID
curl -H "X-Request-ID: debug_req_001" \
  http://localhost:8000/api/v1/momentum/AAPL

# Find in logs
grep "debug_req_001" logs/alphavelocity.log
```

### Example 4: Audit Log Analysis

```bash
# Find all authentication attempts
grep "authentication_attempt" logs/alphavelocity.log

# Find failed authentications
grep "authentication_failure" logs/alphavelocity.log

# Find all admin access
grep "admin_access" logs/alphavelocity.log

# Find all data modifications by user
grep "user_id.*123" logs/alphavelocity.log | grep "resource_"
```

---

## API Endpoints

### Performance Metrics

#### GET /api/v1/metrics/performance

Get performance statistics for all or specific endpoint.

**Query Parameters:**
- `endpoint` (optional) - Specific endpoint path

**Response:**
```json
{
  "success": true,
  "data": {
    "endpoints": [...],
    "total_endpoints": 15
  }
}
```

#### GET /api/v1/metrics/endpoints

Get summary of all endpoints with request counts and average times.

**Response:**
```json
{
  "success": true,
  "summary": {
    "total_endpoints": 15,
    "total_requests": 45678,
    "avg_duration_ms": 234.56
  },
  "endpoints": [...]
}
```

#### GET /api/v1/metrics/slow

Get endpoints exceeding response time threshold.

**Query Parameters:**
- `threshold_ms` (default: 1000) - Threshold in milliseconds

**Response:**
```json
{
  "success": true,
  "threshold_ms": 1000,
  "count": 3,
  "endpoints": [...]
}
```

#### DELETE /api/v1/metrics/performance/reset

Reset performance metrics (admin operation).

**Query Parameters:**
- `endpoint` (optional) - Specific endpoint to reset

**Response:**
```json
{
  "success": true,
  "message": "Performance metrics reset for all endpoints"
}
```

---

## Best Practices

### 1. Request ID Correlation

Always use request IDs for tracking requests across logs:

```python
import requests

response = requests.get(
    "http://localhost:8000/api/v1/momentum/AAPL",
    headers={"X-Request-ID": "debug_001"}
)

# Find in logs
# grep "debug_001" logs/alphavelocity.log
```

### 2. Log Level Configuration

Use appropriate log levels for different environments:

```bash
# Development
LOG_LEVEL=DEBUG

# Staging
LOG_LEVEL=INFO

# Production
LOG_LEVEL=WARNING
```

### 3. Performance Monitoring

Regularly check for slow endpoints:

```bash
# Find slow endpoints
curl http://localhost:8000/api/v1/metrics/slow?threshold_ms=500

# Monitor specific endpoint
curl "http://localhost:8000/api/v1/metrics/performance?endpoint=/api/v1/momentum/{ticker}"
```

### 4. Audit Log Retention

Configure log rotation for audit compliance:

```python
# logging_config.py
handlers = {
    'audit': {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': 'logs/audit.log',
        'maxBytes': 10485760,  # 10MB
        'backupCount': 90,     # Keep 90 days
        'formatter': 'json'
    }
}
```

### 5. Sensitive Data Protection

Never log sensitive data:

```python
# ✓ Good: Data is filtered automatically
logger.info("User login", extra={'username': user.username})

# ✗ Bad: Don't manually log sensitive data
logger.info(f"User login: {user.username}, password: {password}")
```

### 6. Performance Metrics Analysis

Analyze metrics regularly:

```bash
# Weekly performance review
curl http://localhost:8000/api/v1/metrics/endpoints > weekly_metrics.json

# Identify trends
python analyze_metrics.py weekly_metrics.json
```

---

## Troubleshooting

### Issue: Logs Too Verbose

**Problem:** Excessive logging filling up disk space

**Solution:**
```bash
# Reduce log level
LOG_LEVEL=WARNING

# Disable request body logging
LOG_REQUEST_BODY=false

# Increase slow request threshold
LOG_SLOW_REQUEST_THRESHOLD=5000
```

### Issue: Missing Request IDs

**Problem:** Cannot correlate logs across requests

**Solution:**
```python
# Always include request ID in client requests
headers = {"X-Request-ID": generate_request_id()}
response = requests.get(url, headers=headers)
```

### Issue: Sensitive Data in Logs

**Problem:** Passwords or tokens visible in logs

**Solution:**
1. Check `SENSITIVE_FIELDS` configuration
2. Add custom patterns
3. Use structured logging
4. Review log files and purge sensitive data

### Issue: Performance Metrics Not Updating

**Problem:** Metrics seem stale or incorrect

**Solution:**
```bash
# Reset metrics
curl -X DELETE http://localhost:8000/api/v1/metrics/performance/reset

# Check middleware is enabled
grep "PerformanceMiddleware" backend/main.py
```

---

## Security Considerations

### 1. Log Access Control

Restrict access to log files:

```bash
# Set restrictive permissions
chmod 600 logs/*.log

# Only allow application user
chown appuser:appuser logs/*.log
```

### 2. Audit Log Integrity

Ensure audit logs cannot be tampered with:

```bash
# Write-once mode (append only)
chattr +a logs/audit.log

# Use external log aggregation
# Forward to Splunk, ELK, or CloudWatch
```

### 3. PII Protection

Never log personally identifiable information:

- Credit card numbers
- Social Security numbers
- Passwords or password hashes
- API keys or tokens
- Email addresses (unless necessary)
- IP addresses (in high-privacy contexts)

### 4. Log Retention

Follow compliance requirements:

```
GDPR: 90 days for access logs
HIPAA: 6 years for audit logs
PCI-DSS: 1 year for security logs
```

---

**Last Updated:** 2024-01-25
**Version:** 1.0.0
**Maintained By:** AlphaVelocity Team
