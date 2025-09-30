# AlphaVelocity Design Document

## Overview

AlphaVelocity is a Python-based AI momentum scoring engine for stock analysis and portfolio management, specializing in AI supply chain portfolios. The system analyzes stocks using multiple momentum factors and applies these to categorized portfolio allocations.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   React-like    │  │     Charts      │  │     PWA      │ │
│  │   Components    │  │   (Chart.js)    │  │   Features   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│              │                   │                   │      │
│              └─────────────┬─────────────────────────┘      │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                           │ HTTP API
┌───────────────────────────┼─────────────────────────────────┐
│                        Backend                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   FastAPI       │  │    Services     │  │   Database   │ │
│  │   Endpoints     │  │   Layer         │  │ (PostgreSQL) │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│              │                   │                   │      │
│              └─────────────┬─────────────────────────┘      │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                           │
                  ┌─────────┴─────────┐
                  │  External APIs    │
                  │  (Yahoo Finance)  │
                  └───────────────────┘
```

## Core Components

### Backend Architecture

#### 1. FastAPI Application (`backend/main.py`)
- **Role**: Primary API server and routing layer
- **Port**: 8000
- **Features**:
  - RESTful API endpoints
  - CORS middleware for frontend access
  - Automatic OpenAPI documentation
  - Error handling and validation

#### 2. Services Layer (`backend/services/`)

##### MomentumEngine (`momentum_engine.py`)
- **Purpose**: Core momentum scoring algorithm
- **Responsibilities**:
  - Calculate composite momentum scores from multiple factors
  - Price momentum (40% weight)
  - Technical momentum (25% weight)
  - Fundamental momentum (25% weight)
  - Relative momentum (10% weight)
- **Data Sources**: Yahoo Finance via yfinance library

##### PortfolioService (`portfolio_service.py`)
- **Purpose**: Portfolio analysis and management
- **Key Features**:
  - Portfolio composition analysis
  - Category-based allocation tracking
  - Watchlist generation
  - Dollar-value based allocation calculations
- **Categories**: 8 strategic investment categories with target allocations

##### ComparisonService (`comparison_service.py`)
- **Purpose**: Portfolio comparison and analysis
- **Features**:
  - Side-by-side portfolio performance comparison
  - Risk/return analysis
  - Allocation difference visualization

##### Daily Cache Service (`daily_cache_service.py`)
- **Purpose**: Performance optimization through caching
- **Features**:
  - Daily price data caching
  - Momentum score caching
  - Scheduled data updates

##### Database Portfolio Service (`db_portfolio_service.py`)
- **Purpose**: Persistent portfolio management
- **Features**:
  - Transaction tracking
  - Performance history
  - User portfolio management

##### Historical Service (`historical_service.py`)
- **Purpose**: Time-series data management
- **Features**:
  - Historical momentum tracking
  - Performance analytics
  - Trend analysis

#### 3. Models Layer (`backend/models/`)

##### Data Models
- **Portfolio**: Portfolio holdings structure
- **MomentumScore**: Momentum analysis results
- **Comparison**: Portfolio comparison results
- **Historical**: Time-series data structures
- **Database**: PostgreSQL database schemas

#### 4. Database Layer (`backend/database/`)
- **Type**: PostgreSQL (relational database)
- **Purpose**: Persistent data storage
- **Tables**:
  - Users and portfolios
  - Holdings and transactions
  - Performance snapshots
  - Market data cache

### Frontend Architecture

#### 1. Core Application (`frontend/js/app.js`)
- **Type**: Vanilla JavaScript SPA
- **Class**: `AlphaVelocityApp`
- **Features**:
  - Multi-view navigation (Dashboard, Portfolio, Categories, Watchlist, Search, Compare)
  - Real-time data updates
  - Mobile-responsive design
  - PWA capabilities

#### 2. API Client (`frontend/js/api.js`)
- **Class**: `AlphaVelocityAPI`
- **Purpose**: Backend communication layer
- **Features**:
  - HTTP request handling
  - Error management
  - Response processing

#### 3. Chart Manager (`frontend/js/charts.js`)
- **Class**: `ChartManager`
- **Library**: Chart.js
- **Features**:
  - Portfolio allocation pie charts
  - Performance trend line charts
  - Interactive data visualization

#### 4. User Interface
- **Framework**: Vanilla HTML/CSS/JS
- **Styling**: Custom CSS with mobile-first design
- **Features**:
  - Progressive Web App (PWA)
  - Offline functionality
  - Touch-optimized controls

## Data Flow

### 1. Portfolio Analysis Flow
```
User Request → Frontend → API → PortfolioService → MomentumEngine → Yahoo Finance
                ↓
Database ← Services ← FastAPI ← Frontend ← Processed Results
```

### 2. Watchlist Generation Flow
```
Portfolio Holdings → Current Allocation Calculation → Category Gap Analysis → Candidate Scoring → Ranked Recommendations
```

### 3. Real-time Data Flow
```
Daily Scheduler → Yahoo Finance → Cache Service → Database → API Endpoints → Frontend Updates
```

## Key Features

### 1. Momentum Scoring System
- **Multi-factor Analysis**: Combines price, technical, fundamental, and relative momentum
- **Weighted Scoring**: Configurable weights for different momentum factors
- **Rating System**: Converts numerical scores to intuitive ratings (Strong Buy, Buy, Hold, etc.)

### 2. Portfolio Categories
Eight strategic categories with target allocations:
- Large-Cap Anchors (20% allocation, QQQ benchmark)
- Small-Cap Specialists (15% allocation, XLK benchmark)
- Data Center Infrastructure (15% allocation, VNQ benchmark)
- International Tech/Momentum (12% allocation, VEA benchmark)
- Tactical Fixed Income (8% allocation, AGG benchmark)
- Sector Momentum Rotation (10% allocation, SPY benchmark)
- Critical Metals & Mining (7% allocation, XLB benchmark)
- Specialized Materials ETFs (5% allocation, XLB benchmark)

### 3. Watchlist Intelligence
- **Gap Analysis**: Identifies under-allocated categories
- **Priority Scoring**: High/Medium/Low priority based on allocation gaps
- **Candidate Filtering**: Momentum-based stock recommendations
- **Real-time Updates**: Dynamic recalculation based on portfolio changes

### 4. Portfolio Comparison
- **Side-by-side Analysis**: Compare any two portfolios
- **Performance Metrics**: Return, volatility, Sharpe ratio
- **Allocation Breakdown**: Category-level comparison
- **Recommendations**: Actionable insights for portfolio optimization

### 5. Progressive Web App
- **Mobile Optimized**: Touch-friendly interface
- **Offline Capability**: Service worker for offline functionality
- **Installable**: Can be installed as native app
- **Responsive Design**: Adapts to all screen sizes

## API Endpoints

### Core Portfolio APIs
- `GET /` - API health check
- `GET /momentum/{ticker}` - Individual stock momentum score
- `GET /portfolio/analysis` - Default portfolio analysis
- `POST /portfolio/analyze` - Custom portfolio analysis

### Category Management
- `GET /categories` - List all categories
- `GET /categories/{category}/analysis` - Category-specific analysis
- `GET /categories/{category}/tickers` - Category stock list

### Watchlist & Recommendations
- `GET /watchlist` - Generate watchlist for default portfolio
- `POST /watchlist/custom` - Generate watchlist for custom portfolio
- `GET /momentum/top/{limit}` - Top momentum stocks

### Portfolio Comparison
- `POST /compare/portfolios` - Compare two portfolios
- `GET /compare/model-vs-custom` - Compare model vs custom portfolio

### Historical Data
- `GET /historical/momentum/{ticker}` - Historical momentum data
- `GET /historical/portfolio/{id}` - Portfolio performance history
- `GET /historical/performance/{id}` - Performance analytics
- `GET /historical/chart-data/{id}` - Chart-ready data

### Database Operations
- `GET /database/status` - Database connectivity
- `GET /database/portfolios` - User portfolios
- `GET /database/portfolio/{id}/holdings` - Portfolio holdings
- `POST /database/portfolio/{id}/transaction` - Add transaction

### Cache Management
- `GET /cache/status` - Cache status
- `POST /cache/clear` - Clear cache
- `GET /cache/daily/status` - Daily cache status
- `POST /cache/daily/update` - Update daily cache

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Data Source**: Yahoo Finance (yfinance)
- **Database**: PostgreSQL
- **Deployment**: Uvicorn ASGI server
- **Dependencies**: pandas, numpy, datetime

### Frontend
- **Languages**: HTML5, CSS3, JavaScript (ES6+)
- **Charts**: Chart.js
- **PWA**: Service Worker, Web App Manifest
- **Styling**: Custom CSS with mobile-first responsive design

### Development Tools
- **Environment**: VS Code Dev Container
- **Testing**: Python unittest framework
- **Version Control**: Git
- **Package Management**: pip (Python), npm (Node.js tools)

## Performance Optimizations

### 1. Caching Strategy
- **Daily Cache**: Stores price and momentum data for 24-hour periods
- **In-memory Cache**: Fast access to frequently requested data
- **Database Cache**: Persistent storage for historical data

### 2. API Optimization
- **Batch Processing**: Group multiple stock requests
- **Lazy Loading**: Load data only when needed
- **Error Handling**: Graceful degradation for missing data

### 3. Frontend Optimization
- **Mobile-First Design**: Optimized for mobile performance
- **Progressive Loading**: Load critical content first
- **Service Worker**: Offline functionality and caching

## Security Considerations

### 1. Data Protection
- **No Sensitive Data**: No user credentials or personal financial data stored
- **Local Storage**: Portfolio data stored locally in browser
- **CORS Configuration**: Controlled cross-origin access

### 2. API Security
- **Input Validation**: Pydantic models for request validation
- **Error Handling**: Prevents information leakage
- **Rate Limiting**: Implicit through external API limits

## Deployment Architecture

### Development Environment
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **Database**: PostgreSQL database

### Production Considerations
- **Backend**: Containerized FastAPI application
- **Frontend**: Static file serving (CDN recommended)
- **Database**: Scalable to PostgreSQL for production
- **Monitoring**: Built-in health checks and status endpoints

## Future Enhancements

### 1. Short-term Improvements
- Enhanced error handling and retry logic
- Additional momentum factors
- More sophisticated portfolio optimization
- Real-time WebSocket updates

### 2. Long-term Vision
- Machine learning-based momentum predictions
- Multi-user support with authentication
- Advanced portfolio analytics
- Integration with brokerage APIs
- Mobile native applications

## Maintenance & Operations

### 1. Data Updates
- **Scheduled Updates**: Daily cache refresh
- **Manual Refresh**: On-demand data updates
- **Error Recovery**: Automatic retry for failed requests

### 2. Monitoring
- **Health Checks**: Built-in API health endpoints
- **Performance Tracking**: Response time monitoring
- **Error Logging**: Comprehensive error tracking

### 3. Backup & Recovery
- **Database Backups**: PostgreSQL backup procedures
- **Configuration Management**: Version-controlled settings
- **Disaster Recovery**: Data restoration procedures

---

*This design document reflects the current architecture as of the latest commit and serves as a living document for the AlphaVelocity project.*