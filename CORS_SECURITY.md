# CORS Security Configuration

**Date**: 2026-01-24
**Task**: High Priority #3 - Fix CORS Configuration for Production
**Status**: ✅ COMPLETE

---

## Overview

AlphaVelocity now uses a secure, environment-based CORS (Cross-Origin Resource Sharing) configuration that prevents security vulnerabilities while allowing legitimate cross-origin requests.

## Security Issue (Fixed)

### ❌ Previous Configuration (INSECURE)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # DANGEROUS: Allows ANY domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Security Risk**: Wildcard (`*`) CORS origins with credentials enabled is a **critical security vulnerability** that allows:
- Any website to make authenticated requests on behalf of users
- Cross-Site Request Forgery (CSRF) attacks
- Data theft from authenticated sessions
- Unauthorized API access

### ✅ New Configuration (SECURE)
```python
from backend.config.cors_config import setup_cors

setup_cors(app)  # Automatically configures based on environment
```

**Security Benefits**:
- Environment-specific origin validation
- Blocks wildcard origins in production
- Validates origin URL formats
- Comprehensive logging of CORS events
- Automatic security checks on startup

---

## Configuration

### Environment Variables

#### Required for Production

```bash
# CRITICAL: Set this to your actual frontend domain(s)
CORS_ORIGINS=https://app.alphavelocity.com,https://www.alphavelocity.com

# Set environment to production
ENVIRONMENT=production
```

#### Optional Settings

```bash
# Allow credentials (cookies, auth headers) - Default: true
CORS_ALLOW_CREDENTIALS=true

# Allowed HTTP methods - Default: * (all methods)
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,PATCH,OPTIONS

# Allowed headers - Default: * (all headers)
CORS_ALLOW_HEADERS=Content-Type,Authorization,X-Request-ID

# Preflight cache duration (seconds) - Default: 600 (10 min)
CORS_MAX_AGE=600
```

---

## Usage Examples

### Development Setup

```bash
# .env file for local development
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
LOG_LEVEL=DEBUG
```

**Result**: Allows localhost origins, permissive settings for easy development.

### Staging Setup

```bash
# .env file for staging environment
ENVIRONMENT=staging
CORS_ORIGINS=https://staging.alphavelocity.com,https://staging-app.alphavelocity.com
LOG_LEVEL=INFO
JSON_LOGS=true
```

**Result**: Restricted to staging domains, production-like security.

### Production Setup

```bash
# .env file for production
ENVIRONMENT=production
CORS_ORIGINS=https://app.alphavelocity.com,https://www.alphavelocity.com,https://mobile.alphavelocity.com
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
LOG_LEVEL=WARNING
JSON_LOGS=true
```

**Result**: Strict origin validation, production security enforced.

---

## Security Features

### 1. Production Validation

The CORS configuration automatically validates settings on startup:

```python
if is_production():
    if '*' in origins or not origins:
        raise ValueError(
            "SECURITY ERROR: Wildcard CORS origins not allowed in production!"
        )
```

**What this prevents**:
- Accidental deployment with wildcard origins
- Missing CORS configuration in production
- Invalid origin formats

### 2. Origin Format Validation

All origins are validated for proper format:

```python
for origin in origins:
    if not origin.startswith(('http://', 'https://')):
        raise ValueError(f"Invalid origin format: {origin}")
```

**What this prevents**:
- Malformed origin URLs
- Protocol-less origins
- Invalid domain configurations

### 3. Automatic Logging

All CORS events are logged for security monitoring:

```python
logger.info(f"CORS origins configured: {len(origins)} origins")
logger.debug(f"CORS origins: {origins}")  # Only in development
```

**What this enables**:
- Audit trail of CORS configuration
- Detection of configuration issues
- Security event monitoring

### 4. Credential Protection

When credentials are enabled, additional validation ensures origins are specific:

```python
if allow_credentials and '*' in origins:
    # Blocked! Cannot use wildcard with credentials
    raise ValueError("Cannot use wildcard origins with credentials")
```

**What this prevents**:
- Session hijacking
- Cookie theft
- Unauthorized authentication

---

## Testing CORS Configuration

### Check Current Configuration

```bash
# View CORS configuration (development only)
curl http://localhost:8000/cors/config

# Response shows current settings (not implemented in endpoint yet)
```

### Test CORS Request

```bash
# Test from allowed origin
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     http://localhost:8000/api/momentum/NVDA

# Should return CORS headers:
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Credentials: true
```

### Test Rejected Origin

```bash
# Test from disallowed origin
curl -H "Origin: https://evil-site.com" \
     -X OPTIONS \
     http://localhost:8000/api/momentum/NVDA

# Should NOT return Access-Control-Allow-Origin header
```

---

## Common CORS Scenarios

### Scenario 1: Single Frontend Domain

```bash
# Simple production setup
CORS_ORIGINS=https://app.alphavelocity.com
```

### Scenario 2: Multiple Domains/Subdomains

```bash
# Production with multiple frontends
CORS_ORIGINS=https://app.alphavelocity.com,https://mobile.alphavelocity.com,https://admin.alphavelocity.com
```

### Scenario 3: Development + Production Frontend

```bash
# Allow both local development and production
CORS_ORIGINS=http://localhost:3000,https://app.alphavelocity.com
```

### Scenario 4: Mobile App + Web App

```bash
# Native mobile apps might use custom schemes
CORS_ORIGINS=https://app.alphavelocity.com,alphavelocity://app
```

---

## Troubleshooting

### Issue: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Cause**: Your frontend domain is not in `CORS_ORIGINS`

**Solution**:
```bash
# Add your frontend domain to .env
CORS_ORIGINS=https://your-frontend-domain.com
```

### Issue: "SECURITY ERROR: Wildcard CORS origins not allowed"

**Cause**: Running in production without specific CORS origins

**Solution**:
```bash
# Set specific origins in production
ENVIRONMENT=production
CORS_ORIGINS=https://app.alphavelocity.com
```

### Issue: Credentials not being sent

**Cause**: Frontend not configured to send credentials

**Solution**:
```javascript
// Frontend fetch configuration
fetch('https://api.alphavelocity.com/momentum/NVDA', {
    credentials: 'include',  // Include cookies/auth
    headers: {
        'Authorization': 'Bearer ' + token
    }
})
```

### Issue: Preflight request failing

**Cause**: Missing required headers or methods

**Solution**:
```bash
# Allow specific methods and headers
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=Content-Type,Authorization,X-Request-ID
```

---

## Security Best Practices

### ✅ DO

1. **Set specific origins in production**
   ```bash
   CORS_ORIGINS=https://app.alphavelocity.com
   ```

2. **Use HTTPS in production**
   ```bash
   CORS_ORIGINS=https://app.alphavelocity.com  # Not http://
   ```

3. **Minimize allowed origins**
   - Only add origins you control
   - Remove unused origins regularly

4. **Enable credentials only if needed**
   ```bash
   CORS_ALLOW_CREDENTIALS=false  # If you don't need cookies/auth
   ```

5. **Restrict methods if possible**
   ```bash
   CORS_ALLOW_METHODS=GET,POST  # Only what you need
   ```

6. **Monitor CORS logs**
   ```bash
   grep "CORS" logs/alphavelocity.log
   ```

### ❌ DON'T

1. **Never use wildcard in production**
   ```bash
   CORS_ORIGINS=*  # NEVER DO THIS IN PRODUCTION
   ```

2. **Don't mix HTTP and HTTPS carelessly**
   ```bash
   # Bad: Mixing protocols
   CORS_ORIGINS=http://app.example.com,https://app.example.com
   ```

3. **Don't allow credentials with wildcard**
   ```bash
   # Blocked by configuration automatically
   CORS_ORIGINS=*
   CORS_ALLOW_CREDENTIALS=true  # Invalid combination
   ```

4. **Don't forget to update after frontend changes**
   - Update `CORS_ORIGINS` when you change frontend domains
   - Test CORS after domain changes

5. **Don't commit .env files**
   ```bash
   # .env is in .gitignore - keep it there!
   ```

---

## Migration Checklist

For teams migrating from the old CORS configuration:

- [ ] Copy `.env.example` to `.env`
- [ ] Set `CORS_ORIGINS` with your frontend domain(s)
- [ ] Set `ENVIRONMENT=production` for production deployments
- [ ] Test CORS requests from your frontend
- [ ] Verify credentials (cookies/auth) still work
- [ ] Check CORS logs for any issues
- [ ] Update CI/CD pipelines with new environment variables
- [ ] Document CORS configuration for your team
- [ ] Set up monitoring for CORS errors
- [ ] Review and minimize allowed origins quarterly

---

## Monitoring & Alerts

### Log Patterns to Monitor

```bash
# CORS configuration changes
grep "CORS origins configured" logs/alphavelocity.log

# CORS security warnings
grep "CORS" logs/errors.log

# Production security checks
grep "Production CORS configured" logs/alphavelocity.log
```

### Recommended Alerts

Set up alerts for:
1. CORS security errors in production
2. Failed CORS validation on startup
3. Unusual CORS origin requests
4. Changes to CORS configuration

---

## Additional Resources

- [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [OWASP: CORS Security](https://owasp.org/www-community/attacks/CORS_OriginHeaderScrutiny)
- [FastAPI: CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)

---

## Implementation Files

- `/backend/config/cors_config.py` - CORS configuration module
- `/backend/main.py` - Application startup with CORS
- `/.env.example` - Environment variable template
- `/CORS_SECURITY.md` - This documentation

---

**Status**: ✅ CORS security properly configured and production-ready
