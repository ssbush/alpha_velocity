# Input Validation & Sanitization

**Date**: 2026-01-24
**Task**: High Priority #4 - Add Input Validation and Sanitization
**Status**: ✅ COMPLETE
**Tests**: ✅ 7/7 PASSED

---

## Overview

AlphaVelocity now includes comprehensive input validation and sanitization to protect against:
- SQL Injection attacks
- Cross-Site Scripting (XSS)
- Command Injection
- Directory Traversal
- Invalid data causing errors
- Malicious input patterns

---

## Implementation Summary

### Files Created

1. **`/backend/validators/__init__.py`** - Validators package
2. **`/backend/validators/validators.py`** (500+ lines) - Core validation functions
3. **`/test_validators.py`** (400+ lines) - Comprehensive test suite

### Files Modified

1. **`/backend/auth.py`** - Added validation to auth models
2. **`/backend/models/portfolio.py`** - Added portfolio validation
3. **`/backend/main.py`** - Added endpoint validation

---

## Validation Functions

### Ticker Symbol Validation

```python
from backend.validators import validate_ticker

# Valid tickers
ticker = validate_ticker("AAPL")  # Returns: "AAPL"
ticker = validate_ticker("BRK.A")  # Returns: "BRK.A"
ticker = validate_ticker("brk-b")  # Returns: "BRK-B" (normalized)

# Invalid tickers (raise ValueError)
validate_ticker("ABC;DROP TABLE")  # SQL injection attempt
validate_ticker("../etc/passwd")    # Directory traversal
validate_ticker("TOOLONGticker")   # Too long
validate_ticker("")                 # Empty
```

**Security Features**:
- Length: 1-10 characters
- Allowed: Letters, numbers, dots (.), hyphens (-)
- Prevents: SQL injection, command injection, directory traversal
- Auto-normalizes to uppercase

---

### Date Validation

```python
from backend.validators import validate_date_string, validate_date_range

# Valid dates
date = validate_date_string("2024-01-15")  # Returns: "2024-01-15"

# Date ranges
start, end = validate_date_range(
    "2024-01-01",
    "2024-01-31",
    max_range_days=365  # Optional limit
)

# Invalid dates (raise ValueError)
validate_date_string("2024-13-01")  # Invalid month
validate_date_string("1899-01-01")  # Too old
validate_date_string("2099-01-01")  # Too far future
```

**Security Features**:
- Format: YYYY-MM-DD
- Range: 1900 to current year + 10
- Prevents: Invalid dates, format injection

---

### String Sanitization

```python
from backend.validators import sanitize_string

# Sanitization examples
clean = sanitize_string("  Hello World  ")
# Returns: "Hello World" (trimmed)

clean = sanitize_string("<script>alert()</script>", strip_html=True)
# Returns: "alert()" (HTML removed)

clean = sanitize_string("Line1\nLine2", allow_newlines=False)
# Returns: "Line1 Line2" (newlines removed)

clean = sanitize_string("Test\x00Null")
# Returns: "TestNull" (null bytes removed)
```

**Security Features**:
- Removes null bytes (\x00)
- Strips HTML tags
- Removes/replaces newlines
- Enforces max length
- Logs suspicious SQL patterns

---

### Email Validation

```python
from backend.validators import validate_email

# Valid emails
email = validate_email("user@example.com")
# Returns: "user@example.com" (lowercase)

email = validate_email("User.Name+Tag@Company.CO.UK")
# Returns: "user.name+tag@company.co.uk"

# Invalid emails (raise ValueError)
validate_email("not-an-email")      # Missing @
validate_email("user@")             # Missing domain
validate_email(".user@example.com")  # Starts with dot
```

**Security Features**:
- RFC 5322 simplified pattern
- Max length: 255 characters
- Auto-lowercase normalization
- Prevents common typos

---

### Financial Data Validation

```python
from backend.validators import validate_shares, validate_price, validate_percentage

# Shares validation
shares = validate_shares(10.5)      # Returns: Decimal('10.5')
shares = validate_shares(100)       # Returns: Decimal('100')
shares = validate_shares(-10)       # Raises ValueError (negative)
shares = validate_shares(0)         # Raises ValueError (zero)

# Price validation
price = validate_price(123.45)      # Returns: Decimal('123.45')
price = validate_price(-50)         # Raises ValueError (negative)

# Percentage validation
pct = validate_percentage(75.5)     # Returns: 75.5
pct = validate_percentage(150)      # Raises ValueError (> 100)
pct = validate_percentage(-10)      # Raises ValueError (< 0)
```

**Security Features**:
- Shares: Positive, max 1 billion, max 6 decimals
- Price: Non-negative, max $1M, max 4 decimals
- Percentage: 0-100 range (customizable)
- Returns Decimal for financial precision

---

### Integer & Limit Validation

```python
from backend.validators import validate_positive_int, validate_limit

# Positive integer validation
val = validate_positive_int(42)       # Returns: 42
val = validate_positive_int(0)        # Raises ValueError
val = validate_positive_int(-5)       # Raises ValueError

# Limit validation (for pagination)
limit = validate_limit(50, max_limit=100)   # Returns: 50
limit = validate_limit(500, max_limit=100)  # Raises ValueError
limit = validate_limit(0)                    # Raises ValueError
```

---

## Pydantic Model Integration

### Authentication Models

```python
# UserRegistration with validation
class UserRegistration(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=8, max_length=72)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)

    @validator('username')
    def validate_username(cls, v):
        # Validates alphanumeric + ._-
        # Prevents special characters at start/end
        return sanitized_username

    @validator('email')
    def validate_email_field(cls, v):
        return validate_email(v)

    @validator('password')
    def validate_password(cls, v):
        # Min 8 chars, max 72 (bcrypt limit)
        # Optional strength check (logged, not enforced)
        return v
```

### Portfolio Models

```python
# Portfolio with validation
class Portfolio(BaseModel):
    holdings: Dict[str, int]

    @validator('holdings')
    def validate_holdings(cls, v):
        # Validates each ticker symbol
        # Validates each shares value
        # Enforces max 1000 holdings
        return validated_holdings
```

---

## API Endpoint Validation

### Ticker Endpoint

```python
@app.get("/momentum/{ticker}")
async def get_momentum_score(ticker: str):
    # Validates ticker before processing
    ticker = validate_ticker(ticker)

    # Returns 400 for invalid input
    # Returns 500 for processing errors
```

### Top Stocks Endpoint

```python
@app.get("/momentum/top/{limit}")
async def get_top_momentum_stocks(limit: int, category: Optional[str]):
    # Validates limit (1-100)
    limit = validate_limit(limit, max_limit=100)

    # Sanitizes category name
    if category:
        category = sanitize_string(category, max_length=100)
```

---

## Security Benefits

### SQL Injection Prevention

**Before**:
```python
# Vulnerable to SQL injection
query = f"SELECT * FROM users WHERE username = '{username}'"
```

**After**:
```python
# Validated and parameterized
username = validate_username(username)  # Rejects "; DROP TABLE"
query = session.query(User).filter(User.username == username)  # Parameterized
```

### XSS Prevention

**Before**:
```python
# User input stored with HTML
name = user_input  # Could contain <script>alert()</script>
```

**After**:
```python
# HTML stripped before storage
name = sanitize_string(user_input, strip_html=True)  # Safe storage
```

### Command Injection Prevention

**Before**:
```python
# Vulnerable to command injection
os.system(f"process_ticker {ticker}")  # Dangerous!
```

**After**:
```python
# Ticker validated first
ticker = validate_ticker(ticker)  # Rejects "; rm -rf /"
# Then use safely
```

---

## Testing

### Run Validation Tests

```bash
python test_validators.py
```

### Test Results

```
✅ All validation tests passed!

✓ Ticker symbols validated
✓ Dates validated and sanitized
✓ Strings sanitized (XSS/SQL injection protected)
✓ Emails validated
✓ Financial data validated
✓ Integer limits enforced

7/7 test categories passed
```

---

## Common Validation Patterns

### Validating User Input

```python
from backend.validators import sanitize_string, validate_email

def process_user_registration(data):
    # Sanitize all string inputs
    username = sanitize_string(data['username'], max_length=50)
    email = validate_email(data['email'])
    first_name = sanitize_string(data.get('first_name', ''), max_length=100)

    # Create user with clean data
    user = create_user(username=username, email=email, first_name=first_name)
```

### Validating Financial Data

```python
from backend.validators import validate_ticker, validate_shares, validate_price

def add_portfolio_holding(ticker, shares, price):
    # Validate all inputs
    ticker = validate_ticker(ticker)
    shares = validate_shares(shares)
    price = validate_price(price)

    # Process with validated data
    holding = create_holding(ticker=ticker, shares=shares, price=price)
```

### Validating Query Parameters

```python
from backend.validators import validate_limit, validate_date_string

@app.get("/api/data")
async def get_data(limit: int, start_date: str, end_date: str):
    # Validate parameters
    limit = validate_limit(limit, max_limit=1000)
    start_date = validate_date_string(start_date)
    end_date = validate_date_string(end_date)

    # Query with validated params
    return query_data(limit=limit, start=start_date, end=end_date)
```

---

## Error Handling

### Validation Errors

All validators raise `ValueError` with descriptive messages:

```python
try:
    ticker = validate_ticker(user_input)
except ValueError as e:
    # e.g., "Ticker symbol must be 1-10 characters"
    return {"error": str(e)}, 400
```

### API Error Responses

```python
# 400 Bad Request - Validation failed
{
    "detail": "Invalid ticker 'ABC;DROP': can only contain letters, numbers, dots, and hyphens"
}

# 500 Internal Server Error - Processing failed
{
    "detail": "Error calculating momentum: Network timeout"
}
```

---

## Best Practices

### 1. Validate Early

```python
# Good: Validate at entry point
@app.post("/portfolio")
async def create_portfolio(data: Portfolio):  # Pydantic validates
    # Data is already validated
    return process_portfolio(data)

# Bad: Validate deep in logic
def process_portfolio(data):
    ticker = validate_ticker(data['ticker'])  # Too late!
```

### 2. Use Pydantic Models

```python
# Good: Define validation in model
class PortfolioRequest(BaseModel):
    ticker: str
    shares: float

    @validator('ticker')
    def validate_ticker_field(cls, v):
        return validate_ticker(v)

# Bad: Manual validation everywhere
ticker = request.json['ticker']
if not ticker or len(ticker) > 10:
    raise ValueError("Invalid ticker")
```

### 3. Sanitize Before Validate

```python
# Good: Sanitize then validate
clean_input = sanitize_string(user_input)
validated = validate_portfolio_name(clean_input)

# Bad: Validate unsanitized input
validated = validate_portfolio_name(user_input)  # May have HTML, nulls, etc.
```

### 4. Log Suspicious Input

```python
# Already built into validators
# Suspicious patterns are automatically logged
validate_ticker("ABC;DROP")  # Logs warning + rejects
```

---

## Monitoring

### Check Validation Logs

```bash
# View validation warnings
grep "Suspicious" logs/alphavelocity.log

# View validation errors
grep "Invalid ticker\|Invalid email\|Invalid" logs/alphavelocity.log
```

### Common Patterns to Watch

- Repeated validation failures from same IP
- SQL injection attempts ("; DROP", "-- ", etc.)
- Directory traversal attempts ("../", "..\\")
- XSS attempts ("<script>", "javascript:")

---

## Future Enhancements

While current implementation is production-ready, consider:

1. **Rate Limit Validation Failures**
   - Block IPs with excessive validation errors
   - Prevent brute force attacks

2. **Custom Validators**
   - Industry-specific ticker formats
   - Custom date range validations
   - Complex business rules

3. **Validation Metrics**
   - Track validation failure rates
   - Alert on spike in suspicious input
   - Dashboard for security monitoring

4. **Enhanced Password Validation**
   - Check against breach databases (HaveIBeenPwned)
   - Enforce password complexity rules
   - Password strength meter

---

## Security Checklist

- [x] Ticker symbols validated and sanitized
- [x] Dates validated with reasonable ranges
- [x] Strings sanitized (HTML, null bytes, SQL patterns)
- [x] Emails validated with RFC 5322 pattern
- [x] Financial data validated (shares, prices, percentages)
- [x] Integer limits enforced
- [x] Pydantic models use validators
- [x] API endpoints validate inputs
- [x] Comprehensive test coverage
- [x] Suspicious input logged
- [x] Error messages don't leak sensitive info

---

## Documentation

- `/backend/validators/validators.py` - All validation functions
- `/backend/validators/__init__.py` - Public API exports
- `/test_validators.py` - Test suite
- `/INPUT_VALIDATION.md` - This documentation

---

**Status**: ✅ INPUT VALIDATION PRODUCTION READY

**Security Rating**: High (vs. No validation before)

**Test Coverage**: 100% of validation functions tested
