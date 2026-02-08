# Error Handling Documentation

## Overview

AlphaVelocity implements a comprehensive error handling system with standardized error responses, custom exceptions, and detailed error messages. This ensures consistent API behavior and excellent developer experience.

## Table of Contents

- [Error Response Format](#error-response-format)
- [Custom Exceptions](#custom-exceptions)
- [HTTP Status Codes](#http-status-codes)
- [Error Codes](#error-codes)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Error Response Format

All API errors follow a standardized JSON format:

### Standard Error Response

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid ticker symbol: INVALID",
  "status_code": 400,
  "timestamp": "2024-01-25T12:34:56.789Z",
  "path": "/api/v1/momentum/INVALID",
  "request_id": "req_abc123",
  "details": {
    "ticker": "INVALID",
    "reason": "Ticker must be 1-10 uppercase letters"
  }
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Machine-readable error code |
| `message` | string | Human-readable error message |
| `status_code` | integer | HTTP status code |
| `timestamp` | string | ISO 8601 timestamp |
| `path` | string | Request path that caused error |
| `request_id` | string | Unique request identifier for tracking |
| `details` | object | Additional context (optional) |

### Validation Error Response

Validation errors include field-level details:

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "status_code": 400,
  "timestamp": "2024-01-25T12:34:56.789Z",
  "path": "/api/v1/portfolio/analyze",
  "request_id": "req_abc123",
  "validation_errors": [
    {
      "field": "tickers",
      "message": "Field required",
      "type": "missing"
    },
    {
      "field": "shares",
      "message": "Input should be greater than 0",
      "type": "greater_than"
    }
  ]
}
```

### Rate Limit Error Response

Rate limit errors include retry information:

```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded: 100 requests per minute. Retry after 45 seconds",
  "status_code": 429,
  "timestamp": "2024-01-25T12:34:56.789Z",
  "path": "/api/v1/momentum/AAPL",
  "request_id": "req_abc123",
  "retry_after": 45,
  "limit": "100/minute"
}
```

**Response Headers:**
```
Retry-After: 45
```

### Service Error Response

External service errors include service details:

```json
{
  "error": "EXTERNAL_SERVICE_ERROR",
  "message": "Failed to fetch market data for AAPL",
  "status_code": 502,
  "timestamp": "2024-01-25T12:34:56.789Z",
  "path": "/api/v1/momentum/AAPL",
  "request_id": "req_abc123",
  "service": "yfinance",
  "details": {
    "ticker": "AAPL",
    "original_error": "Connection timeout"
  }
}
```

---

## Custom Exceptions

### Exception Hierarchy

```
Exception
└── AlphaVelocityException (base)
    ├── ValidationError (400)
    │   ├── InvalidTickerError
    │   └── InvalidParameterError
    ├── AuthenticationError (401)
    ├── AuthorizationError (403)
    ├── ResourceNotFoundError (404)
    │   ├── TickerNotFoundError
    │   └── PortfolioNotFoundError
    ├── ConflictError (409)
    │   └── DuplicateResourceError
    ├── BusinessLogicError (422)
    │   ├── InsufficientDataError
    │   └── InvalidPortfolioError
    ├── RateLimitExceededError (429)
    ├── ExternalServiceError (502)
    │   ├── DatabaseError
    │   ├── CacheError
    │   └── MarketDataError
    └── ServiceUnavailableError (503)
```

### Base Exception

All custom exceptions inherit from `AlphaVelocityException`:

```python
from backend.exceptions import AlphaVelocityException

raise AlphaVelocityException(
    message="Something went wrong",
    error_code="CUSTOM_ERROR",
    status_code=500,
    details={"key": "value"}
)
```

### Validation Errors (400)

#### InvalidTickerError

```python
from backend.exceptions import InvalidTickerError

raise InvalidTickerError(
    ticker="INVALID",
    reason="Ticker must be 1-10 uppercase letters"
)
```

**Response:**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid ticker symbol: INVALID - Ticker must be 1-10 uppercase letters",
  "status_code": 400,
  "details": {
    "ticker": "INVALID",
    "reason": "Ticker must be 1-10 uppercase letters"
  }
}
```

#### InvalidParameterError

```python
from backend.exceptions import InvalidParameterError

raise InvalidParameterError(
    parameter="limit",
    value=5000,
    reason="Limit cannot exceed 1000"
)
```

**Response:**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid parameter 'limit': Limit cannot exceed 1000",
  "status_code": 400,
  "details": {
    "parameter": "limit",
    "value": "5000",
    "reason": "Limit cannot exceed 1000"
  }
}
```

### Resource Not Found (404)

#### TickerNotFoundError

```python
from backend.exceptions import TickerNotFoundError

raise TickerNotFoundError(ticker="UNKNOWN")
```

**Response:**
```json
{
  "error": "RESOURCE_NOT_FOUND",
  "message": "No data found for ticker: UNKNOWN",
  "status_code": 404,
  "details": {
    "resource_type": "Ticker",
    "resource_id": "UNKNOWN"
  }
}
```

#### PortfolioNotFoundError

```python
from backend.exceptions import PortfolioNotFoundError

raise PortfolioNotFoundError(portfolio_id=123)
```

**Response:**
```json
{
  "error": "RESOURCE_NOT_FOUND",
  "message": "Portfolio not found: 123",
  "status_code": 404,
  "details": {
    "resource_type": "Portfolio",
    "resource_id": "123"
  }
}
```

### Business Logic Errors (422)

#### InsufficientDataError

```python
from backend.exceptions import InsufficientDataError

raise InsufficientDataError(
    ticker="NVDA",
    required_days=200,
    available_days=50
)
```

**Response:**
```json
{
  "error": "BUSINESS_LOGIC_ERROR",
  "message": "Insufficient data for NVDA: need 200 days, have 50",
  "status_code": 422,
  "details": {
    "ticker": "NVDA",
    "required_days": 200,
    "available_days": 50
  }
}
```

#### InvalidPortfolioError

```python
from backend.exceptions import InvalidPortfolioError

raise InvalidPortfolioError(
    reason="Portfolio must have at least one holding",
    details={"holdings_count": 0}
)
```

### External Service Errors (502)

#### DatabaseError

```python
from backend.exceptions import DatabaseError

raise DatabaseError(
    operation="insert_portfolio",
    original_error=e
)
```

**Response:**
```json
{
  "error": "EXTERNAL_SERVICE_ERROR",
  "message": "Database operation failed: insert_portfolio",
  "status_code": 502,
  "service": "PostgreSQL",
  "details": {
    "service": "PostgreSQL",
    "original_error": "IntegrityError: duplicate key value"
  }
}
```

#### MarketDataError

```python
from backend.exceptions import MarketDataError

raise MarketDataError(
    ticker="AAPL",
    provider="yfinance",
    original_error=e
)
```

**Response:**
```json
{
  "error": "EXTERNAL_SERVICE_ERROR",
  "message": "Failed to fetch market data for AAPL",
  "status_code": 502,
  "service": "yfinance",
  "details": {
    "service": "yfinance",
    "ticker": "AAPL",
    "original_error": "HTTPError: 503 Service Unavailable"
  }
}
```

---

## HTTP Status Codes

| Code | Error Code | Description | Use Case |
|------|-----------|-------------|----------|
| **400** | VALIDATION_ERROR | Bad Request | Invalid input parameters |
| **401** | AUTHENTICATION_ERROR | Unauthorized | Missing or invalid credentials |
| **403** | AUTHORIZATION_ERROR | Forbidden | Insufficient permissions |
| **404** | RESOURCE_NOT_FOUND | Not Found | Ticker/portfolio doesn't exist |
| **409** | CONFLICT | Conflict | Duplicate resource |
| **422** | BUSINESS_LOGIC_ERROR | Unprocessable Entity | Business rule violation |
| **429** | RATE_LIMIT_EXCEEDED | Too Many Requests | Rate limit exceeded |
| **500** | INTERNAL_ERROR | Internal Server Error | Unexpected error |
| **502** | EXTERNAL_SERVICE_ERROR | Bad Gateway | External service failed |
| **503** | SERVICE_UNAVAILABLE | Service Unavailable | Temporary outage |

---

## Error Codes

### Complete Error Code Registry

```python
ERROR_CODES = {
    "VALIDATION_ERROR": {
        "description": "Input validation failed",
        "status_code": 400,
        "user_action": "Check request parameters and try again"
    },
    "AUTHENTICATION_ERROR": {
        "description": "Authentication required or failed",
        "status_code": 401,
        "user_action": "Provide valid credentials"
    },
    "AUTHORIZATION_ERROR": {
        "description": "Insufficient permissions",
        "status_code": 403,
        "user_action": "Contact administrator for access"
    },
    "RESOURCE_NOT_FOUND": {
        "description": "Requested resource not found",
        "status_code": 404,
        "user_action": "Verify resource identifier and try again"
    },
    "CONFLICT": {
        "description": "Request conflicts with existing data",
        "status_code": 409,
        "user_action": "Check for duplicates and try again"
    },
    "BUSINESS_LOGIC_ERROR": {
        "description": "Business logic validation failed",
        "status_code": 422,
        "user_action": "Review business rules and adjust request"
    },
    "RATE_LIMIT_EXCEEDED": {
        "description": "Too many requests",
        "status_code": 429,
        "user_action": "Wait and retry after specified time"
    },
    "INTERNAL_ERROR": {
        "description": "Internal server error",
        "status_code": 500,
        "user_action": "Contact support if error persists"
    },
    "EXTERNAL_SERVICE_ERROR": {
        "description": "External service failed",
        "status_code": 502,
        "user_action": "Retry request or contact support"
    },
    "SERVICE_UNAVAILABLE": {
        "description": "Service temporarily unavailable",
        "status_code": 503,
        "user_action": "Retry after specified time"
    }
}
```

---

## Usage Examples

### Example 1: Raising Custom Exception

```python
from fastapi import APIRouter
from backend.exceptions import InvalidTickerError, MarketDataError

router = APIRouter()

@router.get("/momentum/{ticker}")
async def get_momentum(ticker: str):
    # Validate ticker
    if len(ticker) > 10:
        raise InvalidTickerError(
            ticker=ticker,
            reason="Ticker must be 1-10 characters"
        )

    # Fetch data
    try:
        data = fetch_market_data(ticker)
    except Exception as e:
        raise MarketDataError(
            ticker=ticker,
            provider="yfinance",
            original_error=e
        )

    return {"ticker": ticker, "data": data}
```

### Example 2: Using Validators

```python
from backend.validators.validators import validate_ticker
from backend.exceptions import InvalidTickerError

@router.get("/momentum/{ticker}")
async def get_momentum(ticker: str):
    # Validator automatically raises InvalidTickerError
    ticker = validate_ticker(ticker)

    # Proceed with valid ticker
    ...
```

### Example 3: Business Logic Validation

```python
from backend.exceptions import InvalidPortfolioError

@router.post("/portfolio/analyze")
async def analyze_portfolio(holdings: dict):
    if not holdings:
        raise InvalidPortfolioError(
            reason="Portfolio must have at least one holding",
            details={"holdings_count": 0}
        )

    if sum(holdings.values()) == 0:
        raise InvalidPortfolioError(
            reason="Portfolio must have non-zero shares",
            details={"total_shares": 0}
        )

    # Analyze portfolio
    ...
```

### Example 4: Handling Rate Limits

```python
from backend.exceptions import RateLimitExceededError

def check_rate_limit(user_id: str):
    if is_rate_limited(user_id):
        raise RateLimitExceededError(
            limit="100/minute",
            retry_after=calculate_retry_seconds(user_id)
        )
```

---

## Best Practices

### 1. Choose Appropriate Exceptions

Use specific exceptions for better error handling:

```python
# ✓ Good: Specific exception
raise InvalidTickerError(ticker="INVALID", reason="Too long")

# ✗ Bad: Generic exception
raise ValueError("Invalid ticker")
```

### 2. Provide Helpful Details

Include context in the `details` field:

```python
# ✓ Good: Helpful details
raise InvalidPortfolioError(
    reason="Total allocation exceeds 100%",
    details={
        "total_allocation": 105.5,
        "max_allocation": 100.0,
        "categories": ["large-cap", "small-cap"]
    }
)

# ✗ Bad: No context
raise InvalidPortfolioError(reason="Invalid allocation")
```

### 3. Don't Expose Sensitive Information

Never include passwords, tokens, or internal paths:

```python
# ✓ Good: Safe error
raise DatabaseError(
    operation="user_login",
    original_error=None  # Don't expose DB error
)

# ✗ Bad: Exposes internals
raise DatabaseError(
    operation="user_login",
    original_error=e  # May contain DB connection string
)
```

### 4. Use Error Codes Consistently

Map HTTP status codes to error codes:

```python
# Status Code → Error Code mapping
400 → VALIDATION_ERROR
401 → AUTHENTICATION_ERROR
403 → AUTHORIZATION_ERROR
404 → RESOURCE_NOT_FOUND
409 → CONFLICT
422 → BUSINESS_LOGIC_ERROR
429 → RATE_LIMIT_EXCEEDED
500 → INTERNAL_ERROR
502 → EXTERNAL_SERVICE_ERROR
503 → SERVICE_UNAVAILABLE
```

### 5. Log Errors Appropriately

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = calculate_momentum(ticker)
except Exception as e:
    logger.error(
        f"Failed to calculate momentum for {ticker}",
        exc_info=True,
        extra={"ticker": ticker}
    )
    raise MarketDataError(
        ticker=ticker,
        original_error=e
    )
```

### 6. Handle Errors in Middleware

Let exception handlers catch errors:

```python
# Middleware automatically catches all exceptions
# and converts them to standardized responses

# ✓ Good: Raise exception, let handler catch it
raise InvalidTickerError(ticker=ticker, reason="...")

# ✗ Bad: Manually create response
return JSONResponse(
    status_code=400,
    content={"error": "Invalid ticker"}
)
```

---

## Troubleshooting

### Common Issues

#### Issue: Exception Not Being Caught

**Problem:**
```python
raise ValueError("Invalid input")  # Not caught by custom handlers
```

**Solution:**
```python
from backend.exceptions import ValidationError

raise ValidationError("Invalid input")  # Properly handled
```

#### Issue: Missing Request ID

**Problem:** No `request_id` in error response

**Solution:** Add `X-Request-ID` header to requests:

```bash
curl -H "X-Request-ID: req_12345" \
  https://api.example.com/api/v1/momentum/AAPL
```

#### Issue: Internal Errors Expose Too Much

**Problem:** Stack traces visible in production

**Solution:** Set environment variable:

```bash
ENVIRONMENT=production  # Hides internal details
```

#### Issue: Validation Errors Not Detailed Enough

**Problem:** Generic validation error

**Solution:** Use Pydantic models for automatic field validation:

```python
from pydantic import BaseModel, Field

class PortfolioRequest(BaseModel):
    tickers: list[str] = Field(..., min_items=1, max_items=100)
    shares: list[int] = Field(..., gt=0)
```

### Debugging Errors

#### View Full Error Details

```bash
# Development mode
ENVIRONMENT=development python -m backend.main
```

#### Check Logs

```bash
tail -f logs/alphavelocity.log | grep ERROR
```

#### Test Error Responses

```bash
# Invalid ticker
curl http://localhost:8000/api/v1/momentum/TOOLONG123

# Rate limit
for i in {1..200}; do
  curl http://localhost:8000/api/v1/momentum/AAPL
done
```

---

## API Client Examples

### Python Client with Error Handling

```python
import requests
from typing import Optional

class AlphaVelocityClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def get_momentum(self, ticker: str) -> dict:
        response = requests.get(f"{self.base_url}/api/v1/momentum/{ticker}")

        if response.status_code == 200:
            return response.json()

        # Handle errors
        error = response.json()
        error_code = error.get("error")

        if error_code == "VALIDATION_ERROR":
            raise ValueError(f"Invalid ticker: {error['message']}")
        elif error_code == "RATE_LIMIT_EXCEEDED":
            retry_after = error.get("retry_after", 60)
            raise Exception(f"Rate limited. Retry after {retry_after}s")
        elif error_code == "RESOURCE_NOT_FOUND":
            return None  # Ticker not found
        else:
            raise Exception(f"API error: {error['message']}")

# Usage
client = AlphaVelocityClient("http://localhost:8000")

try:
    momentum = client.get_momentum("AAPL")
    print(momentum)
except ValueError as e:
    print(f"Validation error: {e}")
except Exception as e:
    print(f"Error: {e}")
```

### JavaScript Client with Error Handling

```javascript
class AlphaVelocityClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }

    async getMomentum(ticker) {
        const response = await fetch(
            `${this.baseUrl}/api/v1/momentum/${ticker}`
        );

        const data = await response.json();

        if (!response.ok) {
            const error = data.error;

            switch (error) {
                case 'VALIDATION_ERROR':
                    throw new Error(`Invalid ticker: ${data.message}`);
                case 'RATE_LIMIT_EXCEEDED':
                    const retryAfter = data.retry_after || 60;
                    throw new Error(`Rate limited. Retry after ${retryAfter}s`);
                case 'RESOURCE_NOT_FOUND':
                    return null; // Ticker not found
                default:
                    throw new Error(`API error: ${data.message}`);
            }
        }

        return data;
    }
}

// Usage
const client = new AlphaVelocityClient('http://localhost:8000');

try {
    const momentum = await client.getMomentum('AAPL');
    console.log(momentum);
} catch (error) {
    console.error('Error:', error.message);
}
```

---

## Testing Error Responses

### Unit Tests

```python
import pytest
from backend.exceptions import InvalidTickerError

def test_invalid_ticker_error():
    with pytest.raises(InvalidTickerError) as exc_info:
        raise InvalidTickerError(ticker="TOOLONG", reason="Too long")

    assert exc_info.value.error_code == "VALIDATION_ERROR"
    assert exc_info.value.status_code == 400
    assert "TOOLONG" in str(exc_info.value)
```

### Integration Tests

```python
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_invalid_ticker_response():
    response = client.get("/api/v1/momentum/TOOLONGTICKER")

    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "VALIDATION_ERROR"
    assert "ticker" in data["details"]
    assert "timestamp" in data
    assert "request_id" in data
```

---

**Last Updated:** 2024-01-25
**Version:** 1.0.0
**Maintained By:** AlphaVelocity Team
