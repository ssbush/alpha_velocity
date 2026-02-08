# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlphaVelocity is a modern AI-powered momentum scoring engine for stock analysis and portfolio management. The system features a comprehensive FastAPI backend, responsive web frontend, and PostgreSQL database integration, designed for AI supply chain portfolio analysis.

## Architecture Overview

### Backend (`backend/`)
- **FastAPI Application** (`main.py`): RESTful API with 40+ endpoints
- **Services Layer** (`services/`): Business logic modules
  - `momentum_engine.py`: Core momentum scoring algorithm
  - `portfolio_service.py`: Portfolio analysis and management
  - `comparison_service.py`: Portfolio comparison functionality
  - `historical_service.py`: Historical data tracking
  - `daily_scheduler.py`: Automated daily cache updates
- **Models** (`models/`): Pydantic data models and database schemas
- **Database Integration**: PostgreSQL with SQLAlchemy ORM
- **Logging** (`config/logging_config.py`): Structured logging with JSON/colored formatters
- **Middleware** (`middleware/`): Request/response logging, CORS

### Frontend (`frontend/`)
- **Progressive Web App**: Mobile-optimized interface
- **Responsive Design**: Multi-view dashboard with Chart.js visualizations
- **Real-time Features**: Live portfolio tracking and momentum scoring
- **Key Views**: Dashboard, Portfolio, Categories, Watchlist, Search, Compare

### Core Features

#### Momentum Scoring System
The engine calculates weighted momentum scores using:
- **Price Momentum (40%)**: Multi-timeframe returns and moving averages
- **Technical Momentum (25%)**: RSI, volume confirmation, rate of change
- **Fundamental Momentum (25%)**: P/E ratios, growth metrics, analyst ratings
- **Relative Momentum (10%)**: Performance vs. market benchmarks

#### Portfolio Categories
8 strategic AI supply chain categories:
1. **Large-Cap Anchors (20%)** - NVDA, MSFT, META, etc.
2. **Small-Cap Specialists (15%)** - VRT, MOD, BE, etc.
3. **Data Center Infrastructure (15%)** - DLR, SRVR, IRM, etc.
4. **International Tech/Momentum (12%)** - EWJ, EWT, etc.
5. **Tactical Fixed Income (8%)** - SHY, VCIT, etc.
6. **Sector Momentum Rotation (10%)** - XLI, XLE, etc.
7. **Critical Metals & Mining (7%)** - MP, ALB, etc.
8. **Specialized Materials ETFs (5%)** - REMX, LIT, etc.

## Development Commands

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
python -m backend.main
# or
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Access web interface
# Frontend: http://localhost:8000/ (served via static files)
# API docs: http://localhost:8000/docs
```

### Database Setup
```bash
# Setup PostgreSQL database
psql -f setup_db.sql

# Run database migration
python simple_db_migration.py

# Populate portfolio categories
python setup_portfolio_categories.py

# Populate market data
python populate_market_data.py
```

### Testing
```bash
# Test all API endpoints
./test_all_endpoints.sh

# Test database integration
python test_db_endpoints.py

# Test complete integration
python test_complete_integration.py

# Test frontend integration
node test_frontend_integration.js
```

### Data Management
```bash
# Update portfolio holdings
python update_holdings.py

# Test categorized portfolio
node test_categorized_portfolio.js
```

## API Endpoints

### Core Momentum & Portfolio
- `GET /` - Health check
- `GET /momentum/{ticker}` - Get momentum score for ticker
- `GET /portfolio/analysis` - Analyze default portfolio
- `POST /portfolio/analyze` - Analyze custom portfolio
- `GET /categories` - List portfolio categories
- `GET /categories/{name}/analysis` - Analyze category
- `GET /momentum/top/{limit}` - Top momentum stocks

### Historical Data & Analytics
- `GET /historical/momentum/{ticker}` - Momentum history
- `GET /historical/portfolio/{portfolio_id}` - Portfolio performance
- `GET /historical/chart-data/{portfolio_id}` - Chart data
- `POST /historical/backfill` - Backfill historical data

### Database Operations (PostgreSQL)
- `GET /database/status` - Database connection status
- `POST /database/migrate` - Run database migration
- `GET /database/portfolios` - User portfolios
- `POST /database/portfolio/{id}/transaction` - Add transaction
- `GET /database/portfolio/{id}/performance` - Performance history

### Cache Management
- `GET /cache/status` - Cache statistics
- `POST /cache/clear` - Clear cache
- `GET /cache/daily/status` - Daily cache status
- `POST /cache/daily/update` - Manual cache update

## Dependencies

### Core Dependencies
```
fastapi==0.104.1          # Web framework
uvicorn==0.24.0           # ASGI server
pandas==2.1.3             # Data analysis
numpy==1.25.2             # Numerical computing
yfinance==0.2.20          # Financial data
pydantic==2.5.0           # Data validation
```

### Database
```
sqlalchemy==2.0.23        # ORM
psycopg2-binary==2.9.9    # PostgreSQL adapter
alembic==1.12.1           # Database migrations
```

### Security & Auth
```
bcrypt==4.0.1             # Password hashing
python-jose[cryptography]==3.3.0  # JWT tokens
passlib[bcrypt]==1.7.4    # Password utilities
```

### Development & Testing
```
mypy==1.8.0               # Static type checking
pytest==7.4.3             # Testing framework
pytest-asyncio==0.21.1    # Async test support
pytest-cov==4.1.0         # Coverage reporting
```

## Logging

AlphaVelocity uses a comprehensive structured logging system for monitoring and debugging.

### Configuration
Logging is configured via environment variables:
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
- `LOG_DIR`: Log files directory (default: logs/)
- `JSON_LOGS`: Enable JSON formatting for production (default: false)

### Log Files
- `logs/alphavelocity.log`: All application logs (rotates at 10MB, 5 backups)
- `logs/errors.log`: Error-only logs (rotates at 10MB, 5 backups)

### Using Logging in Code
```python
import logging
from backend.config.logging_config import PerformanceLogger

logger = logging.getLogger(__name__)

# Simple logging
logger.info("Processing portfolio analysis")

# Structured logging with context
logger.info(
    "Calculated momentum score",
    extra={'ticker': 'NVDA', 'score': 85.5}
)

# Performance logging
with PerformanceLogger(logger, "Calculate momentum", ticker="NVDA"):
    # Your code here
    pass  # Automatically logs duration
```

### Request Tracing
All API requests include:
- `X-Request-ID` header for correlation
- `X-Process-Time` header showing duration
- Automatic logging of slow requests (>1000ms)

## CORS Security

AlphaVelocity uses environment-based CORS configuration for secure cross-origin requests.

### Configuration
CORS is configured via environment variables in `.env`:

```bash
# Required for production
ENVIRONMENT=production
CORS_ORIGINS=https://app.alphavelocity.com,https://www.alphavelocity.com

# Optional settings
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=*
CORS_ALLOW_HEADERS=*
CORS_MAX_AGE=600
```

### Security Features
- **Production Validation**: Blocks wildcard origins in production
- **Format Validation**: Ensures origins start with http:// or https://
- **Automatic Logging**: All CORS configuration logged
- **Environment-Aware**: Different settings for dev/staging/production

### Usage
```python
from backend.config.cors_config import setup_cors

# In main.py (already configured)
setup_cors(app)  # Automatically sets up based on environment
```

See `CORS_SECURITY.md` for detailed documentation.

## File Structure

```
alpha_velocity/
├── backend/              # FastAPI backend
│   ├── main.py          # Main application
│   ├── services/        # Business logic
│   ├── models/          # Data models
│   ├── database/        # Database config
│   ├── middleware/      # Request/response middleware
│   ├── config/          # Configuration (logging, etc.)
│   ├── auth.py          # Authentication utilities
│   └── utils/           # Utilities
├── frontend/            # Web interface
│   ├── index.html       # Main page
│   ├── css/            # Styles
│   ├── js/             # JavaScript
│   └── assets/         # Static assets
├── logs/               # Application logs (gitignored)
├── data/               # Data files
├── scripts/            # Utility scripts
├── tests/              # Test files
└── docs/               # Documentation
```

## Development Environment

- **Python 3.11.2**
- **Dev Container**: VS Code with Python extensions
- **Database**: PostgreSQL 13+
- **Testing**: unittest framework
- **Formatting**: Enabled via VS Code settings