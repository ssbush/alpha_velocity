# CI/CD Pipeline Documentation

## Overview

AlphaVelocity uses GitHub Actions for Continuous Integration and Continuous Deployment (CI/CD). This document outlines the complete CI/CD pipeline, workflows, best practices, and deployment procedures.

## Table of Contents

- [CI/CD Architecture](#cicd-architecture)
- [GitHub Actions Workflows](#github-actions-workflows)
- [Local Development](#local-development)
- [Testing Strategy](#testing-strategy)
- [Deployment Process](#deployment-process)
- [Docker Integration](#docker-integration)
- [Monitoring and Rollback](#monitoring-and-rollback)
- [Secrets Management](#secrets-management)
- [Best Practices](#best-practices)

---

## CI/CD Architecture

### Pipeline Stages

```
┌─────────────────────────────────────────────────────────────┐
│                      Code Push / PR                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    CI Pipeline                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Linting    │  │   Testing    │  │   Security   │      │
│  │  - Black     │  │  - Unit      │  │  - Safety    │      │
│  │  - isort     │  │  - Integration│  │  - Bandit   │      │
│  │  - Flake8    │  │  - API       │  │              │      │
│  │  - MyPy      │  │  - Coverage  │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Build & Package                          │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ Docker Image │  │  Artifacts   │                         │
│  │    Build     │  │  Generation  │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Deployment                               │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │   Staging    │  │  Production  │                         │
│  │  (Auto/PR)   │  │  (Tag/Manual)│                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

---

## GitHub Actions Workflows

### 1. CI Pipeline (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**

#### a) Code Quality (`lint`)

Checks code formatting, linting, and type safety:

```yaml
- Black: Code formatting check
- isort: Import sorting check
- Flake8: Python linting
- MyPy: Static type checking
```

**Run locally:**
```bash
make format-check
make lint
```

#### b) Unit & Integration Tests (`test`)

Runs comprehensive test suite with PostgreSQL and Redis:

```yaml
Services:
  - PostgreSQL 13
  - Redis 7

Tests:
  - Unit tests (isolated, fast)
  - Integration tests (database, cache)
  - Coverage report (70% minimum)
```

**Run locally:**
```bash
make test
make test-cov
```

#### c) API Integration Tests (`api-tests`)

Tests all API endpoints:

```yaml
- Starts FastAPI server
- Tests all endpoints with test_all_endpoints.sh
- Validates response formats
```

**Run locally:**
```bash
make run &
sleep 10
make api-test
```

#### d) Security Scanning (`security`)

Scans for vulnerabilities:

```yaml
- Safety: Dependency vulnerability check
- Bandit: Security linting for code
```

**Run locally:**
```bash
make security
```

#### e) Build Status Summary (`build-status`)

Aggregates all job results and reports overall build status.

---

### 2. Deployment Pipeline (`.github/workflows/deploy.yml`)

**Triggers:**
- Tag push: `v*.*.*` (e.g., `v1.2.3`)
- Manual workflow dispatch with environment selection

**Jobs:**

#### a) Validate Release (`validate`)

Validates version tags and dependencies:

```bash
# Tag format validation
v1.2.3  ✓ Valid
v1.2    ✗ Invalid
1.2.3   ✗ Invalid (missing 'v')
```

#### b) Build Docker Image (`build`)

Builds and pushes Docker images:

```yaml
Registry: Docker Hub
Tags:
  - v1.2.3 (exact version)
  - v1.2 (minor version)
  - v1 (major version)
  - latest (default branch)
  - main-sha123 (commit SHA)
```

**Build caching:**
- Uses registry cache for faster builds
- Cache key: `buildcache`

#### c) Deploy to Staging (`deploy-staging`)

Automatic deployment to staging environment:

```yaml
Trigger: Manual dispatch (environment=staging) or push to develop
URL: https://staging.alphavelocity.com
Steps:
  1. SSH to staging server
  2. Pull latest Docker images
  3. Run docker-compose up
  4. Run database migrations
  5. Execute smoke tests
  6. Send Slack notification
```

#### d) Deploy to Production (`deploy-production`)

Manual/tag-based deployment to production:

```yaml
Trigger: Tag push (v*.*.*) or manual dispatch (environment=production)
URL: https://alphavelocity.com
Protection: Requires environment approval
Steps:
  1. Create GitHub deployment
  2. SSH to production server
  3. Backup database
  4. Pull latest Docker images
  5. Run docker-compose up
  6. Run database migrations
  7. Health check
  8. Update deployment status
  9. Run smoke tests
  10. Send Slack notification
```

#### e) Rollback (`rollback`)

Manual rollback process (triggers on deployment failure):

```yaml
Steps:
  1. Stop current containers
  2. Restore previous Docker images
  3. Optionally restore database backup
  4. Send notification
```

---

## Local Development

### Setup

1. **Install dependencies:**
   ```bash
   make install
   make install-dev
   ```

2. **Setup environment:**
   ```bash
   make setup
   # Edit .env with your configuration
   ```

3. **Install pre-commit hooks:**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

### Development Workflow

```bash
# 1. Make code changes
vim backend/services/momentum_engine.py

# 2. Format code
make format

# 3. Run linters
make lint

# 4. Run tests
make test

# 5. Check coverage
make test-cov

# 6. Run all CI checks locally
make ci

# 7. Commit (pre-commit hooks will run automatically)
git add .
git commit -m "Add feature X"
git push
```

### Pre-commit Hooks

Automatically run on `git commit`:

```yaml
Hooks:
  - trailing-whitespace: Remove trailing whitespace
  - end-of-file-fixer: Ensure files end with newline
  - check-yaml: Validate YAML syntax
  - check-json: Validate JSON syntax
  - black: Format Python code
  - isort: Sort imports
  - flake8: Lint Python code
  - mypy: Type checking
  - bandit: Security linting
  - detect-secrets: Prevent secret commits
```

**Bypass hooks (not recommended):**
```bash
git commit -m "Message" --no-verify
```

---

## Testing Strategy

### Test Pyramid

```
         ┌─────────────┐
         │     E2E     │  10% - Full system tests
         │   (Manual)  │
         └─────────────┘
       ┌─────────────────┐
       │  Integration    │  20% - API, DB, Cache
       │     Tests       │
       └─────────────────┘
     ┌─────────────────────┐
     │    Unit Tests       │  70% - Fast, isolated
     └─────────────────────┘
```

### Test Categories

#### 1. Unit Tests (`@pytest.mark.unit`)

Fast, isolated tests for individual functions:

```python
# backend/tests/test_momentum_engine.py
@pytest.mark.unit
def test_calculate_momentum_score():
    engine = MomentumEngine()
    score = engine.calculate_momentum_score("AAPL")
    assert score['overall_momentum_score'] > 0
```

**Run:**
```bash
pytest -m unit
```

#### 2. Integration Tests (`@pytest.mark.integration`)

Tests with external services (database, Redis):

```python
# backend/tests/test_database_integration.py
@pytest.mark.integration
@pytest.mark.database
def test_portfolio_persistence(db_session):
    portfolio = create_portfolio(db_session, "Test Portfolio")
    assert portfolio.id is not None
```

**Run:**
```bash
pytest -m integration
```

#### 3. API Tests (`@pytest.mark.api`)

Tests for API endpoints:

```python
# backend/tests/test_api_endpoints.py
@pytest.mark.api
async def test_momentum_endpoint(client):
    response = await client.get("/api/v1/momentum/AAPL")
    assert response.status_code == 200
    assert "overall_momentum_score" in response.json()
```

**Run:**
```bash
pytest -m api
```

### Coverage Requirements

- **Minimum Coverage:** 70%
- **Target Coverage:** 85%
- **Critical Paths:** 90%+

**Check coverage:**
```bash
make test-cov
open htmlcov/index.html
```

---

## Deployment Process

### Staging Deployment

**Automatic on push to `develop`:**

```bash
git checkout develop
git merge feature-branch
git push origin develop
# Workflow automatically deploys to staging
```

**Manual deployment:**

```bash
# Via GitHub CLI
gh workflow run deploy.yml -f environment=staging

# Via Makefile
make deploy-staging
```

### Production Deployment

**Version Tag Method (Recommended):**

```bash
# 1. Create version tag
git tag -a v1.2.3 -m "Release version 1.2.3"

# 2. Push tag
git push origin v1.2.3

# 3. Workflow automatically:
#    - Validates tag format
#    - Builds Docker image
#    - Deploys to production
#    - Runs smoke tests
```

**Manual Deployment:**

```bash
# Via GitHub CLI (requires approval)
gh workflow run deploy.yml -f environment=production

# Via Makefile (interactive confirmation)
make deploy-prod
```

### Deployment Checklist

Before production deployment:

- [ ] All CI checks pass
- [ ] Code reviewed and approved
- [ ] Database migrations tested
- [ ] .env secrets updated
- [ ] Monitoring configured
- [ ] Rollback plan ready
- [ ] Stakeholders notified
- [ ] Smoke tests prepared

---

## Docker Integration

### Docker Compose Services

```yaml
services:
  postgres:   # PostgreSQL database
  redis:      # Redis cache
  app:        # FastAPI application
  nginx:      # Reverse proxy (optional)
```

### Development with Docker

**Start all services:**
```bash
make docker-up
# or
docker-compose up -d
```

**View logs:**
```bash
make docker-logs
# or
docker-compose logs -f app
```

**Stop services:**
```bash
make docker-down
# or
docker-compose down
```

**Clean everything:**
```bash
make docker-clean
# Removes containers, volumes, and images
```

### Production Docker Deployment

**On production server:**

```bash
# 1. Pull latest images
docker-compose pull

# 2. Backup database
docker-compose exec postgres pg_dump \
  -U alphavelocity alphavelocity > backup.sql

# 3. Start services
docker-compose up -d

# 4. Run migrations
docker-compose exec app python simple_db_migration.py

# 5. Health check
curl -f http://localhost:8000/
```

---

## Monitoring and Rollback

### Health Checks

**API Health:**
```bash
curl -f https://alphavelocity.com/
```

**Database Health:**
```bash
curl https://alphavelocity.com/database/status
```

**Cache Health:**
```bash
curl https://alphavelocity.com/api/v1/cache/stats
```

### Rollback Procedures

#### 1. Docker Image Rollback

```bash
# List recent images
docker images alphavelocity

# Tag previous version as latest
docker tag alphavelocity:v1.2.2 alphavelocity:latest

# Restart containers
docker-compose up -d
```

#### 2. Database Rollback

```bash
# Restore from backup
docker-compose exec -T postgres psql \
  -U alphavelocity alphavelocity < backup_20240115_120000.sql
```

#### 3. Git Rollback

```bash
# Revert to previous commit
git revert HEAD

# Or reset to previous tag
git reset --hard v1.2.2
git push --force origin main
```

---

## Secrets Management

### Required Secrets

Configure in GitHub Settings → Secrets and variables → Actions:

#### Docker Hub
```
DOCKER_USERNAME: Docker Hub username
DOCKER_PASSWORD: Docker Hub password/token
```

#### Staging Environment
```
STAGING_HOST: staging.alphavelocity.com
STAGING_USER: deploy
STAGING_SSH_KEY: SSH private key for deployment
```

#### Production Environment
```
PRODUCTION_HOST: alphavelocity.com
PRODUCTION_USER: deploy
PRODUCTION_SSH_KEY: SSH private key for deployment
```

#### Notifications
```
SLACK_WEBHOOK: Slack webhook URL for notifications
```

#### Application Secrets (Server)
```
# In .env on server
JWT_SECRET_KEY: Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
DB_PASSWORD: Strong database password
REDIS_PASSWORD: Redis password (if enabled)
```

### Secret Rotation

**Quarterly rotation schedule:**

1. **Generate new secrets:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update in GitHub Secrets**

3. **Deploy to staging and test**

4. **Deploy to production during maintenance window**

5. **Verify functionality**

---

## Best Practices

### 1. Branching Strategy

```
main        Production-ready code
  ↑
develop     Integration branch
  ↑
feature/*   Feature branches
hotfix/*    Critical fixes
```

**Workflow:**
```bash
# Create feature branch
git checkout -b feature/add-momentum-cache

# Develop and test
make ci

# Create PR to develop
gh pr create --base develop

# After approval, merge to develop
# CI runs automatically

# When ready for production, merge develop to main
# Create release tag
git tag v1.3.0
git push origin v1.3.0
```

### 2. Commit Messages

Follow conventional commits:

```
feat: Add concurrent momentum calculation
fix: Resolve cache invalidation bug
docs: Update API documentation
test: Add unit tests for portfolio service
refactor: Optimize database queries
perf: Improve batch processing performance
chore: Update dependencies
```

### 3. Version Numbering

Follow Semantic Versioning (SemVer):

```
v1.2.3
 │ │ │
 │ │ └── Patch: Bug fixes, minor changes
 │ └──── Minor: New features, backward compatible
 └────── Major: Breaking changes
```

### 4. Testing Guidelines

- **Write tests first** (TDD when possible)
- **Keep tests fast** (< 1 second per unit test)
- **Mock external services** in unit tests
- **Use fixtures** for common test data
- **Name tests descriptively:** `test_should_return_error_when_ticker_invalid`

### 5. Code Review Checklist

- [ ] Code follows style guide (Black, isort)
- [ ] Tests added for new features
- [ ] Coverage meets minimum threshold
- [ ] No security vulnerabilities
- [ ] Documentation updated
- [ ] No hardcoded secrets
- [ ] Error handling implemented
- [ ] Logging added for debugging

### 6. Deployment Best Practices

- **Deploy during low-traffic periods**
- **Monitor metrics after deployment**
- **Keep rollback plan ready**
- **Communicate with team**
- **Test in staging first**
- **Use feature flags for risky features**

---

## Troubleshooting

### Common CI Failures

#### 1. Black Formatting Failure

```bash
# Error: would reformat backend/main.py
# Fix:
make format
git add .
git commit -m "Fix formatting"
```

#### 2. Import Sorting Failure

```bash
# Error: Imports are incorrectly sorted
# Fix:
isort backend/
git add .
git commit -m "Fix import sorting"
```

#### 3. Test Failures

```bash
# Run tests locally to debug
pytest -v --lf  # Run last failed tests
pytest -v --pdb  # Drop into debugger on failure
```

#### 4. Coverage Below Threshold

```bash
# Generate coverage report
make test-cov
open htmlcov/index.html

# Add tests for uncovered code
vim backend/tests/test_new_feature.py
```

### Common Deployment Issues

#### 1. Docker Build Fails

```bash
# Check Dockerfile syntax
docker build -t alphavelocity:test .

# Clear build cache
docker builder prune
```

#### 2. Database Migration Fails

```bash
# Check migration script
python simple_db_migration.py

# Rollback and retry
# (Manual database intervention may be required)
```

#### 3. Health Check Fails

```bash
# Check application logs
docker-compose logs app

# Check service status
docker-compose ps

# Restart services
docker-compose restart app
```

---

## Performance Metrics

### CI Pipeline Performance

```
Job                  Target Time    Typical Time
────────────────────────────────────────────────
Lint                 < 2 min        1 min 30s
Unit Tests           < 3 min        2 min 15s
Integration Tests    < 5 min        4 min 00s
API Tests            < 3 min        2 min 30s
Security Scan        < 2 min        1 min 45s
────────────────────────────────────────────────
Total CI Time        < 10 min       8 min 00s
```

### Deployment Performance

```
Deployment Type      Target Time    Typical Time
────────────────────────────────────────────────
Staging              < 5 min        3 min 30s
Production           < 10 min       7 min 00s
Rollback             < 3 min        2 min 00s
```

---

## Additional Resources

### Documentation
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [Pytest Documentation](https://docs.pytest.org/)

### Tools
- **GitHub CLI:** `gh` - Manage workflows from terminal
- **Docker Compose:** Multi-container orchestration
- **Pre-commit:** Git hook framework
- **Make:** Task automation

### Support
- **Issues:** Report bugs and issues on GitHub
- **Discussions:** Ask questions in GitHub Discussions
- **Slack:** Team communication channel

---

## Changelog

### v1.0.0 (2024-01-25)
- Initial CI/CD pipeline implementation
- GitHub Actions workflows for CI and deployment
- Docker containerization
- Pre-commit hooks
- Comprehensive testing framework
- Automated staging and production deployment

---

**Last Updated:** 2024-01-25
**Maintained By:** AlphaVelocity Team
**Version:** 1.0.0
