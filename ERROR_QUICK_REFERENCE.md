# Error Handling Quick Reference

Quick reference for error handling in AlphaVelocity API.

## Common Error Responses

### Invalid Ticker

**Request:**
```bash
GET /api/v1/momentum/TOOLONGTICKER
```

**Response: 400**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid ticker symbol: TOOLONGTICKER - Ticker symbol must be 1-10 characters",
  "status_code": 400,
  "timestamp": "2024-01-25T12:34:56.789Z",
  "path": "/api/v1/momentum/TOOLONGTICKER",
  "details": {
    "ticker": "TOOLONGTICKER",
    "reason": "Ticker symbol must be 1-10 characters"
  }
}
```

---

### Ticker Not Found

**Request:**
```bash
GET /api/v1/momentum/UNKNOWN
```

**Response: 404**
```json
{
  "error": "RESOURCE_NOT_FOUND",
  "message": "No data found for ticker: UNKNOWN",
  "status_code": 404,
  "timestamp": "2024-01-25T12:34:56.789Z",
  "path": "/api/v1/momentum/UNKNOWN",
  "details": {
    "resource_type": "Ticker",
    "resource_id": "UNKNOWN"
  }
}
```

---

### Rate Limit Exceeded

**Request:**
```bash
# After 100 requests in 1 minute
GET /api/v1/momentum/AAPL
```

**Response: 429**
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded: 100/minute. Retry after 45 seconds",
  "status_code": 429,
  "timestamp": "2024-01-25T12:34:56.789Z",
  "path": "/api/v1/momentum/AAPL",
  "retry_after": 45,
  "limit": "100/minute"
}
```

**Headers:**
```
Retry-After: 45
```

---

### Validation Error (Pydantic)

**Request:**
```bash
POST /api/v1/momentum/batch
Content-Type: application/json

{
  "tickers": []
}
```

**Response: 400**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "status_code": 400,
  "timestamp": "2024-01-25T12:34:56.789Z",
  "path": "/api/v1/momentum/batch",
  "validation_errors": [
    {
      "field": "tickers",
      "message": "List should have at least 1 item after validation",
      "type": "too_short"
    }
  ]
}
```

---

### Market Data Unavailable

**Request:**
```bash
GET /api/v1/momentum/AAPL
```

**Response: 502**
```json
{
  "error": "EXTERNAL_SERVICE_ERROR",
  "message": "Failed to fetch market data for AAPL",
  "status_code": 502,
  "timestamp": "2024-01-25T12:34:56.789Z",
  "path": "/api/v1/momentum/AAPL",
  "service": "yfinance",
  "details": {
    "ticker": "AAPL",
    "original_error": "HTTPError: 503 Service Unavailable"
  }
}
```

---

### Insufficient Data

**Request:**
```bash
GET /api/v1/momentum/NEWIPO
```

**Response: 422**
```json
{
  "error": "BUSINESS_LOGIC_ERROR",
  "message": "Insufficient data for NEWIPO: need 200 days, have 10",
  "status_code": 422,
  "timestamp": "2024-01-25T12:34:56.789Z",
  "path": "/api/v1/momentum/NEWIPO",
  "details": {
    "ticker": "NEWIPO",
    "required_days": 200,
    "available_days": 10
  }
}
```

---

### Internal Server Error

**Request:**
```bash
GET /api/v1/momentum/AAPL
```

**Response: 500**
```json
{
  "error": "INTERNAL_ERROR",
  "message": "An internal server error occurred",
  "status_code": 500,
  "timestamp": "2024-01-25T12:34:56.789Z",
  "path": "/api/v1/momentum/AAPL",
  "details": {
    "error_type": "Exception"
  }
}
```

**Note:** In development, includes more details:
```json
{
  "error": "INTERNAL_ERROR",
  "message": "Internal error: Division by zero",
  "status_code": 500,
  "details": {
    "error_type": "ZeroDivisionError",
    "traceback": "Traceback (most recent call last):\n  ..."
  }
}
```

---

## Python Examples

### Raising Exceptions

```python
from backend.exceptions import (
    InvalidTickerError,
    TickerNotFoundError,
    MarketDataError,
    InsufficientDataError
)

# Invalid ticker
raise InvalidTickerError(
    ticker="TOOLONG",
    reason="Ticker must be 1-10 characters"
)

# Ticker not found
raise TickerNotFoundError(ticker="UNKNOWN")

# Market data error
try:
    data = fetch_data(ticker)
except Exception as e:
    raise MarketDataError(
        ticker=ticker,
        provider="yfinance",
        original_error=e
    )

# Insufficient data
raise InsufficientDataError(
    ticker=ticker,
    required_days=200,
    available_days=50
)
```

### Using Validators

```python
from backend.validators.validators import validate_ticker
from backend.exceptions import InvalidTickerError

@router.get("/momentum/{ticker}")
async def get_momentum(ticker: str):
    # Automatically raises InvalidTickerError if invalid
    ticker = validate_ticker(ticker)

    # Proceed with valid ticker
    ...
```

---

## HTTP Status Code Reference

| Code | Error Code | When to Use |
|------|-----------|-------------|
| 400 | VALIDATION_ERROR | Invalid input, bad parameters |
| 401 | AUTHENTICATION_ERROR | Missing/invalid credentials |
| 403 | AUTHORIZATION_ERROR | Insufficient permissions |
| 404 | RESOURCE_NOT_FOUND | Ticker/portfolio not found |
| 409 | CONFLICT | Duplicate resource |
| 422 | BUSINESS_LOGIC_ERROR | Valid input, business rule violation |
| 429 | RATE_LIMIT_EXCEEDED | Too many requests |
| 500 | INTERNAL_ERROR | Unexpected server error |
| 502 | EXTERNAL_SERVICE_ERROR | External API failed |
| 503 | SERVICE_UNAVAILABLE | Temporary outage |

---

## Client Error Handling

### Python

```python
import requests

response = requests.get("http://localhost:8000/api/v1/momentum/AAPL")

if response.ok:
    data = response.json()
else:
    error = response.json()
    error_code = error.get("error")

    if error_code == "RATE_LIMIT_EXCEEDED":
        retry_after = error.get("retry_after", 60)
        print(f"Rate limited. Retry after {retry_after}s")
    elif error_code == "RESOURCE_NOT_FOUND":
        print(f"Ticker not found: {error['message']}")
    else:
        print(f"Error: {error['message']}")
```

### JavaScript

```javascript
const response = await fetch('http://localhost:8000/api/v1/momentum/AAPL');
const data = await response.json();

if (!response.ok) {
    const { error, message, retry_after } = data;

    switch (error) {
        case 'RATE_LIMIT_EXCEEDED':
            console.log(`Rate limited. Retry after ${retry_after}s`);
            break;
        case 'RESOURCE_NOT_FOUND':
            console.log(`Ticker not found: ${message}`);
            break;
        default:
            console.error(`Error: ${message}`);
    }
}
```

### curl

```bash
# Extract error code from response
curl -s http://localhost:8000/api/v1/momentum/INVALID | jq '.error'
# Output: "VALIDATION_ERROR"

# Extract error message
curl -s http://localhost:8000/api/v1/momentum/INVALID | jq '.message'
# Output: "Invalid ticker symbol: INVALID - ..."

# Extract retry_after for rate limits
curl -s http://localhost:8000/api/v1/momentum/AAPL | jq '.retry_after'
# Output: 45 (or null if not rate limited)
```

---

## Testing

### Test Invalid Input

```bash
# Invalid ticker (too long)
curl http://localhost:8000/api/v1/momentum/TOOLONGTICKER

# Invalid ticker (special chars)
curl http://localhost:8000/api/v1/momentum/AAPL%3BDROP

# Empty ticker
curl http://localhost:8000/api/v1/momentum/
```

### Test Rate Limiting

```bash
# Trigger rate limit
for i in {1..150}; do
  curl http://localhost:8000/api/v1/momentum/AAPL
done
```

### Test Validation Errors

```bash
# Missing required field
curl -X POST http://localhost:8000/api/v1/momentum/batch \
  -H "Content-Type: application/json" \
  -d '{}'

# Invalid field value
curl -X POST http://localhost:8000/api/v1/momentum/batch \
  -H "Content-Type: application/json" \
  -d '{"tickers": []}'
```

---

## Environment Variables

### Development

```bash
ENVIRONMENT=development  # Shows detailed errors with stack traces
LOG_LEVEL=DEBUG         # Verbose logging
```

### Production

```bash
ENVIRONMENT=production  # Hides internal details
LOG_LEVEL=WARNING      # Minimal logging
```

---

## Debugging

### View Error Logs

```bash
# Tail error logs
tail -f logs/alphavelocity.log | grep ERROR

# Filter by request ID
tail -f logs/alphavelocity.log | grep "req_abc123"
```

### Add Request ID

```bash
# Include request ID in request
curl -H "X-Request-ID: my_debug_req_123" \
  http://localhost:8000/api/v1/momentum/AAPL

# Find in logs
grep "my_debug_req_123" logs/alphavelocity.log
```

---

## Quick Fixes

### "Invalid ticker symbol"
- Check ticker length (1-10 characters)
- Use uppercase letters only
- Remove special characters (except . and -)

### "Rate limit exceeded"
- Wait for `retry_after` seconds
- Use authenticated endpoints for higher limits
- Implement exponential backoff

### "Ticker not found"
- Verify ticker symbol is correct
- Check if ticker is delisted or inactive
- Try alternative ticker symbols

### "Insufficient data"
- Use older, established tickers
- Avoid newly IPO'd stocks
- Check if enough historical data exists

---

**Quick Tip:** Always check the `error_code` field for programmatic error handling, not the HTTP status code alone.
