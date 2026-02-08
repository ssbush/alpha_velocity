.PHONY: help install test lint format clean docker-build docker-up docker-down migrate ci deploy

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)AlphaVelocity - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Development
install: ## Install dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	pip install pytest pytest-cov pytest-asyncio pytest-mock
	pip install black isort flake8 mypy
	pip install safety bandit
	@echo "$(GREEN)✓ Development dependencies installed$(NC)"

setup: install ## Initial setup (install + create .env)
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✓ Created .env file$(NC)"; \
	else \
		echo "$(YELLOW)⚠ .env file already exists$(NC)"; \
	fi
	@echo "$(GREEN)✓ Setup complete$(NC)"

# Testing
test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest backend/tests/ -v
	@echo "$(GREEN)✓ Tests completed$(NC)"

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	pytest backend/tests/ -v -m unit
	@echo "$(GREEN)✓ Unit tests completed$(NC)"

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest backend/tests/ -v -m integration
	@echo "$(GREEN)✓ Integration tests completed$(NC)"

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest backend/tests/ --cov=backend --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"

test-watch: ## Run tests in watch mode
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	pytest-watch backend/tests/ -v

# Code Quality
lint: ## Run all linters
	@echo "$(BLUE)Running linters...$(NC)"
	flake8 backend/
	mypy backend/ --ignore-missing-imports
	@echo "$(GREEN)✓ Linting completed$(NC)"

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	black backend/
	isort backend/
	@echo "$(GREEN)✓ Code formatted$(NC)"

format-check: ## Check code formatting without changes
	@echo "$(BLUE)Checking code formatting...$(NC)"
	black --check backend/
	isort --check-only backend/
	@echo "$(GREEN)✓ Formatting check passed$(NC)"

security: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	safety check
	bandit -r backend/ -ll
	@echo "$(GREEN)✓ Security checks completed$(NC)"

# CI/CD
ci: format-check lint test-cov security ## Run all CI checks locally
	@echo "$(GREEN)✓ All CI checks passed$(NC)"

# Database
migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	python simple_db_migration.py
	@echo "$(GREEN)✓ Migrations completed$(NC)"

db-setup: ## Setup database (requires PostgreSQL)
	@echo "$(BLUE)Setting up database...$(NC)"
	psql -f setup_db.sql
	python simple_db_migration.py
	@echo "$(GREEN)✓ Database setup completed$(NC)"

# Docker
docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build
	@echo "$(GREEN)✓ Docker images built$(NC)"

docker-up: ## Start Docker containers
	@echo "$(BLUE)Starting Docker containers...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Containers started$(NC)"

docker-down: ## Stop Docker containers
	@echo "$(BLUE)Stopping Docker containers...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Containers stopped$(NC)"

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-clean: ## Remove Docker containers and volumes
	@echo "$(BLUE)Cleaning Docker containers and volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)✓ Docker cleaned$(NC)"

# Running
run: ## Run FastAPI development server
	@echo "$(BLUE)Starting development server...$(NC)"
	python -m backend.main

run-prod: ## Run FastAPI production server
	@echo "$(BLUE)Starting production server...$(NC)"
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4

run-docker: docker-up ## Run application in Docker

# Cleaning
clean: ## Clean up generated files
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ .coverage coverage.xml
	@echo "$(GREEN)✓ Cleanup completed$(NC)"

# Deployment
deploy-staging: ## Deploy to staging environment
	@echo "$(BLUE)Deploying to staging...$(NC)"
	@echo "$(YELLOW)⚠ This will trigger the staging deployment workflow$(NC)"
	gh workflow run deploy.yml -f environment=staging

deploy-prod: ## Deploy to production environment
	@echo "$(RED)⚠ WARNING: Deploying to PRODUCTION$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BLUE)Deploying to production...$(NC)"; \
		gh workflow run deploy.yml -f environment=production; \
	else \
		echo "$(YELLOW)Deployment cancelled$(NC)"; \
	fi

# Cache management
cache-warmup: ## Warmup cache with popular tickers
	@echo "$(BLUE)Warming up cache...$(NC)"
	curl -X POST "http://localhost:8000/api/v1/cache/warmup?tickers=AAPL,NVDA,MSFT,GOOGL,TSLA,META,AMZN,AMD,AVGO,QCOM"
	@echo "$(GREEN)✓ Cache warmed up$(NC)"

cache-clear: ## Clear all cache
	@echo "$(BLUE)Clearing cache...$(NC)"
	curl -X DELETE "http://localhost:8000/api/v1/cache/clear"
	@echo "$(GREEN)✓ Cache cleared$(NC)"

# API testing
api-test: ## Test API endpoints
	@echo "$(BLUE)Testing API endpoints...$(NC)"
	bash test_all_endpoints.sh
	@echo "$(GREEN)✓ API tests completed$(NC)"

# Documentation
docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	@echo "$(YELLOW)Documentation generation not yet implemented$(NC)"

# Version bump
version-patch: ## Bump patch version (1.0.0 -> 1.0.1)
	@echo "$(BLUE)Bumping patch version...$(NC)"
	@echo "$(YELLOW)Version bumping not yet implemented$(NC)"

version-minor: ## Bump minor version (1.0.0 -> 1.1.0)
	@echo "$(BLUE)Bumping minor version...$(NC)"
	@echo "$(YELLOW)Version bumping not yet implemented$(NC)"

version-major: ## Bump major version (1.0.0 -> 2.0.0)
	@echo "$(BLUE)Bumping major version...$(NC)"
	@echo "$(YELLOW)Version bumping not yet implemented$(NC)"
