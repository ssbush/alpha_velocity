# Alpha Velocity - TODO List

**Last Updated**: 2026-02-09
**Status**: Active Development

---

## High Priority (Critical for Production Readiness)

### 1. Type Hints
- [x] Add type hints to core services (momentum, portfolio, comparison, user) *(2026-01-24)*
- [x] Add mypy to requirements *(2026-01-24)*
- [ ] Add type hints to `backend/services/historical_service.py`
- [ ] Add type hints to `backend/services/user_portfolio_service.py`
- [ ] Add type hints to `backend/services/category_service.py`
- [ ] Add type hints to `backend/main.py` endpoint functions
- [ ] Run mypy and fix all type errors

### 2. Test Coverage
- [x] pytest, pytest-asyncio, pytest-cov configured *(2026-02-08)*
- [x] Momentum engine unit tests (5 tests) *(2026-02-08)*
- [x] Portfolio service unit tests (7 tests) *(2026-02-08)*
- [x] API endpoint integration tests (14 tests) *(2026-02-08)*
- [x] Validator tests (7 tests) *(2026-02-08)*
- [x] Test fixtures in conftest.py *(2026-02-08)*
- [x] Auth module tests — JWT tokens, password hashing, Pydantic models (45 tests) *(2026-02-09)*
- [x] Auth endpoint tests — register, login, refresh, profile (15 tests) *(2026-02-09)*
- [x] Exception hierarchy tests (31 tests) *(2026-02-09)*
- [x] Error response model tests (22 tests) *(2026-02-09)*
- [x] Error handler tests (9 tests) *(2026-02-09)*
- [x] Extended validator tests — dates, sanitization, portfolio names (65 tests) *(2026-02-09)*
- [x] Middleware tests — logging, audit, performance (moved from backend/tests/) *(2026-02-09)*
- [x] Cache decorator tests (17 tests) *(2026-02-09)*
- [x] Cache service tests — InMemoryCache + CacheService (23 tests) *(2026-02-09)*
- [x] Rate limit config tests (18 tests) *(2026-02-09)*
- [x] CORS config tests (9 tests) *(2026-02-09)*
- [x] Concurrent utilities tests (23 tests) *(2026-02-09)*
- [x] Logging config tests — JSONFormatter, PerformanceLogger (12 tests) *(2026-02-09)*
- [x] Database config tests (11 tests) *(2026-02-09)*
- [x] Data provider tests (6 tests) *(2026-02-09)*
- [x] User service tests (10 tests) *(2026-02-09)*
- [x] Pagination tests (26 tests) *(2026-02-09)*
- [x] Main.py endpoint tests — legacy routes (31 tests) *(2026-02-09)*
- [x] API v1 endpoint tests — cache, metrics, categories, batch (24 tests) *(2026-02-09)*
- [x] Coverage at 70.50% — `--cov-fail-under=70` passes (473 tests, 0 skipped) *(2026-02-09)*
- [ ] Add database model and relationship tests (requires PostgreSQL integration tests)

### 3. Security Hardening
- [x] SECRET_KEY enforcement (crash in production if missing) *(2026-02-08)*
- [x] Short-lived access tokens (1 hour) with 7-day refresh tokens *(2026-02-08)*
- [x] Password strength enforcement (uppercase + lowercase + digit) *(2026-02-08)*
- [x] Token type validation (access vs refresh) *(2026-02-08)*
- [x] CORS environment-based configuration *(2026-01-24)*
- [x] Rate limiting on all endpoints *(2026-01-24)*
- [x] Input validation and sanitization *(2026-01-24)*
- [x] Add security headers middleware (HSTS, CSP, X-Frame-Options) *(2026-02-09)*
- [x] Implement account lockout after failed login attempts *(2026-02-10)*
- [ ] Add CSRF protection for state-changing endpoints
- [x] Add refresh token rotation (issue new refresh token on each refresh) *(2026-02-10)*

### 4. Environment & Configuration
- [x] `.env.example` with all variables documented *(2026-02-08)*
- [x] SECRET_KEY documentation fixed to match code *(2026-02-08)*
- [x] Environment-aware behavior (dev vs production) *(2026-02-08)*
- [ ] Add startup validation for all critical environment variables
- [ ] Document deployment configuration for common platforms (AWS, Railway, etc.)

---

## Medium Priority (Production Enhancement)

### 5. API Versioning
- [x] v1 router created with momentum, portfolio, categories, cache, metrics endpoints *(2026-01-24)*
- [ ] Migrate frontend to use `/api/v1/` prefixed endpoints
- [ ] Deprecate unversioned endpoints with warning headers
- [ ] Document versioning strategy for consumers

### 6. Pagination
- [x] Pagination utility created (`backend/utils/pagination.py`) *(2026-01-24)*
- [x] Paginated momentum and portfolio endpoints in v1 *(2026-01-24)*
- [ ] Apply pagination to transaction history endpoints
- [ ] Apply pagination to historical data endpoints
- [ ] Update frontend to handle paginated responses

### 7. Redis Caching
- [x] Redis cache layer with decorators (`backend/cache/`) *(2026-01-24)*
- [x] Cache configuration in `.env.example` *(2026-01-24)*
- [ ] Deploy and test with actual Redis instance
- [ ] Tune TTLs based on production usage patterns
- [ ] Monitor cache hit rates and optimize

### 8. CI/CD Pipeline
- [x] GitHub Actions workflows (ci, deploy, dependency-check) *(2026-01-24)*
- [x] Pre-commit hooks configuration *(2026-01-24)*
- [x] Docker and docker-compose setup *(2026-01-24)*
- [ ] Verify CI workflow runs tests successfully on GitHub
- [ ] Add security scanning (bandit, safety) to CI
- [ ] Configure Dependabot for automatic dependency updates
- [ ] Set up staging environment deployment

### 9. Error Handling
- [x] Custom exception hierarchy (`backend/exceptions.py`) *(2026-01-24)*
- [x] Structured error models (`backend/models/error_models.py`) *(2026-01-24)*
- [x] Error handlers registered *(2026-01-24)*
- [ ] Audit all endpoints for consistent error handling
- [x] Fix: `momentum_batch.py` catches `ValueError` but `validate_ticker` raises `InvalidTickerError` *(2026-02-09)*
- [x] Fix: `InMemoryCache.clear()` doesn't accept `pattern` argument *(2026-02-09)*
- [x] Fix: `PerformanceMetrics.get_all_stats()` deadlock — re-entrant lock *(2026-02-09)*
- [ ] Add error code documentation for API consumers

### 10. Logging & Monitoring
- [x] Structured logging with JSON/colored formatters *(2026-01-24)*
- [x] Request/response logging middleware *(2026-01-24)*
- [x] Audit middleware *(2026-01-24)*
- [x] Performance monitoring middleware *(2026-01-24)*
- [ ] Replace remaining `print()` in migration scripts
- [ ] Integrate APM tool (Sentry/DataDog) for production monitoring
- [ ] Set up alerts for error rate spikes and slow requests

---

## Low Priority (Nice to Have)

### 11. Frontend Improvements
- [x] Remove hardcoded `localhost:8000` URLs *(2026-02-08)*
- [x] Configurable API base URL via `window.ALPHAVELOCITY_API_URL` *(2026-02-08)*
- [x] Auto-refresh access token on 401 *(2026-02-08)*
- [ ] Evaluate frontend framework migration (React/Vue/Svelte)
- [ ] Add modern build pipeline (Vite)
- [ ] Implement virtual scrolling for large lists
- [ ] Add service worker caching strategy

### 12. WebSocket Support
- [ ] Add WebSocket endpoint for real-time momentum score updates
- [ ] Push portfolio value changes to connected clients
- [ ] Add WebSocket authentication

### 13. Database Improvements
- [ ] Set up Alembic for schema migrations
- [ ] Add database indexes for common queries
- [ ] Optimize N+1 queries with eager loading
- [ ] Add database connection health checks and monitoring

### 14. Advanced Security
- [ ] Two-factor authentication (2FA)
- [ ] API key management for external service consumers
- [ ] Audit logging for sensitive operations (already have middleware, needs review)
- [ ] Data encryption at rest
- [ ] GDPR/PII compliance review

### 15. Documentation
- [ ] System architecture diagram
- [ ] Database schema diagram (ERD)
- [ ] API usage examples and guides
- [ ] Authentication flow documentation
- [ ] Deployment and operations runbook

---

## Code Quality

- [ ] Extract hardcoded `DEFAULT_PORTFOLIO` to config/constants
- [ ] Centralize price fetching logic into dedicated service
- [ ] Remove duplicate code in portfolio services
- [ ] Consolidate API response formatting
- [ ] Add docstrings to all public functions

---

## Progress Summary

| Priority | Done | Total | Progress |
|----------|------|-------|----------|
| High     | 4/4  | 4     | 100%     |
| Medium   | 3/6  | 6     | 50%      |
| Low      | 1/5  | 5     | 20%      |

**Next up**: Security headers middleware, account lockout, fix InvalidTickerError in batch endpoints, migrate frontend to /api/v1/.
