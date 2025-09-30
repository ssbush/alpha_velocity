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

### Security & Auth (planned)
```
bcrypt==4.0.1             # Password hashing
python-jose[cryptography]==3.3.0  # JWT tokens
passlib[bcrypt]==1.7.4    # Password utilities
```

## File Structure

```
alpha_velocity/
├── backend/              # FastAPI backend
│   ├── main.py          # Main application
│   ├── services/        # Business logic
│   ├── models/          # Data models
│   ├── database/        # Database config
│   └── utils/           # Utilities
├── frontend/            # Web interface
│   ├── index.html       # Main page
│   ├── css/            # Styles
│   ├── js/             # JavaScript
│   └── assets/         # Static assets
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