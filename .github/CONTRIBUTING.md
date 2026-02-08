# Contributing to AlphaVelocity

Thank you for your interest in contributing to AlphaVelocity! This guide will help you get started.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [CI/CD Pipeline](#cicd-pipeline)

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Redis 7+ (optional for development)
- Git
- Docker and Docker Compose (optional)

### Setup Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/alphavelocity.git
   cd alphavelocity
   ```

2. **Install dependencies:**
   ```bash
   make install
   make install-dev
   ```

3. **Setup environment:**
   ```bash
   make setup
   # Edit .env with your local configuration
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

5. **Run database migrations:**
   ```bash
   make migrate
   ```

6. **Start the development server:**
   ```bash
   make run
   ```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Write your code following our [code standards](#code-standards).

### 3. Format Code

```bash
make format
```

### 4. Run Tests

```bash
make test
make test-cov
```

### 5. Run All CI Checks

```bash
make ci
```

This runs:
- Code formatting check (Black, isort)
- Linting (Flake8, MyPy)
- Tests with coverage
- Security checks

### 6. Commit Changes

```bash
git add .
git commit -m "feat: add your feature"
```

Pre-commit hooks will automatically run. Fix any issues they report.

### 7. Push and Create PR

```bash
git push origin feature/your-feature-name
gh pr create --base develop --title "Add your feature"
```

---

## Code Standards

### Python Style Guide

We follow **PEP 8** with the following tools:

- **Black:** Code formatter (line length: 100)
- **isort:** Import sorting
- **Flake8:** Linting (max complexity: 10)
- **MyPy:** Type checking

### Commit Message Format

Use **Conventional Commits:**

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

**Examples:**
```
feat(api): add batch momentum endpoint
fix(cache): resolve Redis connection timeout
docs: update API documentation
test(momentum): add unit tests for edge cases
```

### Type Hints

Always use type hints:

```python
def calculate_momentum(ticker: str, period: int = 30) -> Dict[str, float]:
    """Calculate momentum score for a ticker."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def analyze_portfolio(holdings: Dict[str, int]) -> PortfolioAnalysis:
    """
    Analyze portfolio holdings and calculate metrics.

    Args:
        holdings: Dictionary mapping ticker symbols to share counts

    Returns:
        PortfolioAnalysis object with metrics and recommendations

    Raises:
        ValueError: If holdings is empty or contains invalid tickers
    """
    ...
```

---

## Testing

### Test Categories

#### Unit Tests

Fast, isolated tests:

```python
@pytest.mark.unit
def test_calculate_momentum_score():
    engine = MomentumEngine()
    score = engine.calculate_momentum_score("AAPL")
    assert score['overall_momentum_score'] > 0
```

#### Integration Tests

Tests with external services:

```python
@pytest.mark.integration
@pytest.mark.database
def test_portfolio_crud(db_session):
    portfolio = create_portfolio(db_session, "Test")
    assert portfolio.id is not None
```

#### API Tests

Endpoint testing:

```python
@pytest.mark.api
async def test_momentum_endpoint(client):
    response = await client.get("/api/v1/momentum/AAPL")
    assert response.status_code == 200
```

### Running Tests

```bash
# All tests
make test

# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# With coverage
make test-cov

# Specific test file
pytest backend/tests/test_momentum_engine.py

# Specific test
pytest backend/tests/test_momentum_engine.py::test_calculate_score
```

### Coverage Requirements

- **Minimum:** 70%
- **Target:** 85%
- **Critical paths:** 90%+

All PRs must maintain or improve coverage.

---

## Submitting Changes

### Pull Request Process

1. **Update your branch:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout feature/your-feature
   git rebase develop
   ```

2. **Ensure all checks pass:**
   ```bash
   make ci
   ```

3. **Create Pull Request:**
   ```bash
   gh pr create --base develop
   ```

4. **Fill out PR template:**
   - Description of changes
   - Related issues
   - Testing performed
   - Screenshots (if UI changes)

5. **Request review:**
   Assign at least one reviewer

### PR Requirements

- [ ] All CI checks pass
- [ ] Code coverage maintained or improved
- [ ] Tests added for new features
- [ ] Documentation updated
- [ ] No merge conflicts
- [ ] Approved by at least one reviewer

---

## CI/CD Pipeline

### Continuous Integration

On every push and PR, GitHub Actions runs:

1. **Linting:** Black, isort, Flake8, MyPy
2. **Testing:** Unit, integration, API tests
3. **Security:** Safety, Bandit scans
4. **Coverage:** Minimum 70% required

**Pipeline stages:**
```
Code Push → Lint → Test → Security → Build Status
```

### Continuous Deployment

#### Staging

Automatic deployment on merge to `develop`:

```bash
git checkout develop
git merge feature/your-feature
git push origin develop
# Automatically deploys to staging
```

#### Production

Tag-based deployment:

```bash
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3
# Automatically deploys to production
```

### Monitoring CI/CD

- **GitHub Actions:** Check workflow runs
- **Codecov:** View coverage reports
- **Artifacts:** Download test results

---

## Code Review Guidelines

### For Authors

- Keep PRs small and focused
- Write descriptive commit messages
- Add tests for new functionality
- Update documentation
- Respond to feedback promptly

### For Reviewers

- Review code thoroughly
- Test changes locally if needed
- Provide constructive feedback
- Approve only when satisfied
- Use GitHub's review features

---

## Getting Help

- **Documentation:** See `docs/` directory
- **Issues:** Search existing issues
- **Discussions:** Ask questions in GitHub Discussions
- **Slack:** Join team channel (if applicable)

---

## License

By contributing, you agree that your contributions will be licensed under the project's license.

---

**Thank you for contributing to AlphaVelocity!**
