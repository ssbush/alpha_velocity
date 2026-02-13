from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging
import os

# Initialize logging first (before other imports)
from .config.logging_config import setup_logging
from .config.cors_config import setup_cors
from .config.security_headers_config import setup_security_headers
from .config.rate_limit_config import (
    limiter,
    rate_limit_exceeded_handler,
    RateLimits,
    log_rate_limit_config
)
from .config.account_lockout_config import login_attempt_tracker, log_lockout_config
from .config.token_rotation_config import refresh_token_tracker, log_token_rotation_config
from .config.csrf_config import log_csrf_config

# Setup logging based on environment
setup_logging(
    log_level=os.getenv('LOG_LEVEL', 'INFO'),
    json_logs=os.getenv('JSON_LOGS', 'false').lower() == 'true',
    console_output=True
)

logger = logging.getLogger(__name__)

from .config.env_validation import validate_environment
validate_environment()

from .services.price_service import PriceService, set_price_service
from .services.momentum_engine import MomentumEngine
from .services.portfolio_service import PortfolioService
from .services.comparison_service import ComparisonService
from .services.daily_scheduler import initialize_scheduler, get_scheduler
from .services.category_service import CategoryService
from .middleware.logging_middleware import LoggingMiddleware
from .models.momentum import MomentumScore
from .models.portfolio import (
    PortfolioAnalysis, CategoryInfo, CategoryAnalysis,
    Portfolio, PortfolioHolding
)
from .models.historical import (
    MomentumTrendData, PortfolioHistory, PerformanceAnalytics,
    TopPerformer, MomentumHistoryEntry
)
from .models.comparison import PortfolioComparison

# Initialize FastAPI app
app = FastAPI(
    title="AlphaVelocity API",
    description="""
    AI Supply Chain Momentum Scoring Engine

    ## API Versioning

    This API uses versioning to ensure backward compatibility:
    - **v1**: `/api/v1/` - Current stable version (recommended)
    - **Legacy**: Root-level endpoints (deprecated, use v1 instead)

    ## Features

    - **Momentum Scoring**: Calculate momentum scores for stocks
    - **Portfolio Analysis**: Analyze portfolio holdings and allocations
    - **Category Management**: Manage and analyze portfolio categories
    - **Cache Management**: Monitor and control price caching

    ## Rate Limiting

    - Public API: 100 requests/minute
    - Authenticated API: 200 requests/minute
    - Expensive operations: 10 requests/minute
    - Administrative operations: 5 requests/minute

    ## Authentication

    Protected endpoints require JWT token in Authorization header:
    ```
    Authorization: Bearer <token>
    ```
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "v1",
            "description": "Version 1 API endpoints (recommended)"
        },
        {
            "name": "momentum",
            "description": "Momentum scoring operations"
        },
        {
            "name": "portfolio",
            "description": "Portfolio analysis operations"
        },
        {
            "name": "categories",
            "description": "Category management operations"
        },
        {
            "name": "cache",
            "description": "Cache management operations"
        },
        {
            "name": "legacy",
            "description": "Legacy endpoints (deprecated, use /api/v1/ instead)"
        }
    ]
)

# Setup secure CORS middleware (environment-based configuration)
setup_cors(app)

# Setup security response headers (HSTS, CSP, X-Frame-Options, etc.)
setup_security_headers(app)

# Add middleware stack (order matters - last added is executed first)
# 1. Performance monitoring (outermost - tracks total time)
from .middleware.performance_middleware import PerformanceMiddleware
app.add_middleware(PerformanceMiddleware, enable_logging=True, log_threshold_ms=5000)

# 2. Audit logging (security events)
from .middleware.audit_middleware import AuditMiddleware
app.add_middleware(AuditMiddleware, enable_audit=True, log_all_requests=False)

# 3. CSRF protection (double-submit cookie)
from .middleware.csrf_middleware import CSRFMiddleware
app.add_middleware(CSRFMiddleware)

# 4. Deprecation warnings for legacy unversioned endpoints
from .middleware.deprecation_middleware import DeprecationMiddleware
app.add_middleware(DeprecationMiddleware)

# 5. Request/response logging (detailed logging)
app.add_middleware(LoggingMiddleware)

# Register exception handlers for standardized error responses
from .error_handlers import register_exception_handlers
register_exception_handlers(app)

# Add rate limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
app.state.limiter = limiter
# Note: RateLimitExceeded handler is registered in error_handlers.py

# Log rate limit configuration
log_rate_limit_config()

# Log account lockout configuration
log_lockout_config()

# Log token rotation configuration
log_token_rotation_config()

# Log CSRF protection configuration
log_csrf_config()

# Include API versioning
from .api import api_router
app.include_router(api_router, prefix="/api")

logger.info("API versioning enabled - v1 endpoints available at /api/v1/")

from .config.portfolio_config import DEFAULT_PORTFOLIO

# Initialize services
price_service = PriceService()
set_price_service(price_service)
momentum_engine = MomentumEngine(price_service=price_service)
portfolio_service = PortfolioService(momentum_engine, price_service=price_service)
comparison_service = ComparisonService(portfolio_service)

# Database services (optional, loaded on demand)
try:
    from .database.config import db_config
    # Test if database is available
    DATABASE_AVAILABLE = db_config.test_connection()
    if DATABASE_AVAILABLE:
        logger.info("Database connection successful - User authentication enabled")
    else:
        logger.warning("Database connection failed - Running in file mode only")
except Exception as e:
    logger.warning(f"Database initialization failed: {e}", exc_info=True)
    DATABASE_AVAILABLE = False

# Keep simple_db_service for legacy endpoints
try:
    from .simple_db_service import get_database_service
    db_service = get_database_service()
except Exception as e:
    logger.warning(f"Database service initialization failed: {e}", exc_info=True)
    db_service = None

# Get all portfolio tickers for caching
def get_all_portfolio_tickers() -> List[str]:
    """Get all unique tickers from default portfolio and categories"""
    all_tickers = set(DEFAULT_PORTFOLIO.keys())

    # Add category tickers
    try:
        categories = portfolio_service.get_all_categories()
        for category_info in categories.values():
            all_tickers.update(category_info['tickers'])
    except Exception as e:
        logger.warning(f"Could not load category tickers: {e}", exc_info=True)

    return list(all_tickers)

# Initialize daily cache scheduler
PORTFOLIO_TICKERS = get_all_portfolio_tickers()
daily_scheduler = initialize_scheduler(momentum_engine, PORTFOLIO_TICKERS, price_service=price_service)

logger.info(
    f"AlphaVelocity initialized with {len(PORTFOLIO_TICKERS)} tickers for daily caching",
    extra={'ticker_count': len(PORTFOLIO_TICKERS), 'tickers': sorted(PORTFOLIO_TICKERS)}
)

@app.get("/")
async def root() -> dict:
    """API health check"""
    return {"message": "AlphaVelocity API is running", "version": "1.0.0"}

@app.get("/momentum/{ticker}", response_model=MomentumScore)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_momentum_score(request: Request, ticker: str) -> MomentumScore:
    """Get momentum score for a specific ticker"""
    from .validators.validators import validate_ticker

    from .exceptions import InvalidTickerError

    try:
        # Validate ticker symbol
        ticker = validate_ticker(ticker)

        result = momentum_engine.calculate_momentum_score(ticker)
        return MomentumScore(**result)
    except (ValueError, InvalidTickerError) as e:
        # Input validation error
        raise HTTPException(status_code=400, detail=f"Invalid ticker: {str(e)}")
    except Exception as e:
        logger.error(f"Error calculating momentum for {ticker}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculating momentum: {str(e)}")

@app.get("/portfolio/analysis")
async def analyze_portfolio(portfolio_data: Optional[str] = None) -> PortfolioAnalysis:
    """Analyze portfolio holdings (uses default if none provided)"""
    try:
        # Use default portfolio if none provided
        portfolio = DEFAULT_PORTFOLIO

        df, total_value, avg_score = portfolio_service.analyze_portfolio(portfolio)

        holdings = [PortfolioHolding(**h) for h in PortfolioService.dataframe_to_holdings(df)]

        return PortfolioAnalysis(
            holdings=holdings,
            total_value=total_value,
            average_momentum_score=avg_score,
            number_of_positions=len(portfolio)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing portfolio: {str(e)}")

@app.post("/portfolio/analyze")
@limiter.limit(RateLimits.EXPENSIVE)
async def analyze_custom_portfolio(request: Request, portfolio: Portfolio) -> PortfolioAnalysis:
    """Analyze custom portfolio holdings"""
    try:
        if not portfolio.holdings:
            raise HTTPException(status_code=400, detail="Portfolio cannot be empty")

        df, total_value, avg_score = portfolio_service.analyze_portfolio(portfolio.holdings)

        holdings = [PortfolioHolding(**h) for h in PortfolioService.dataframe_to_holdings(df)]

        return PortfolioAnalysis(
            holdings=holdings,
            total_value=total_value,
            average_momentum_score=avg_score,
            number_of_positions=len(portfolio.holdings)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing custom portfolio: {str(e)}")

@app.get("/portfolio/analysis/by-categories")
async def analyze_portfolio_by_categories() -> dict:
    """Analyze default portfolio with holdings grouped by categories"""
    try:
        portfolio = DEFAULT_PORTFOLIO
        result = portfolio_service.get_portfolio_by_categories(portfolio)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing portfolio by categories: {str(e)}")

@app.post("/portfolio/analyze/by-categories")
async def analyze_custom_portfolio_by_categories(portfolio: Portfolio) -> dict:
    """Analyze custom portfolio with holdings grouped by categories"""
    try:
        if not portfolio.holdings:
            raise HTTPException(status_code=400, detail="Portfolio cannot be empty")

        result = portfolio_service.get_portfolio_by_categories(portfolio.holdings)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing custom portfolio by categories: {str(e)}")

@app.get("/categories", response_model=List[CategoryInfo])
async def get_categories() -> list:
    """Get all portfolio categories"""
    try:
        categories = portfolio_service.get_all_categories()
        result = []
        for name, info in categories.items():
            result.append(CategoryInfo(
                name=name,
                tickers=info['tickers'],
                target_allocation=info['target_allocation'],
                benchmark=info['benchmark']
            ))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")

@app.get("/categories/{category_name}/analysis", response_model=CategoryAnalysis)
async def analyze_category(category_name: str) -> CategoryAnalysis:
    """Analyze a specific portfolio category"""
    try:
        result = portfolio_service.get_categories_analysis(category_name)
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])

        return CategoryAnalysis(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing category {category_name}: {str(e)}")

@app.get("/momentum/top/{limit}")
async def get_top_momentum_stocks(limit: int = 10, category: Optional[str] = None) -> list:
    """Get top momentum stocks, optionally filtered by category"""
    from .validators.validators import validate_limit, sanitize_string

    try:
        # Validate limit parameter
        limit = validate_limit(limit, max_limit=100)

        # Validate category if provided
        if category:
            category = sanitize_string(category, max_length=100, allow_newlines=False)

        result = portfolio_service.get_top_momentum_stocks(category, limit)
        return result
    except ValueError as e:
        # Input validation error
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error fetching top momentum stocks", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching top momentum stocks: {str(e)}")

@app.get("/categories/{category_name}/tickers")
async def get_category_tickers(category_name: str) -> dict:
    """Get tickers for a specific category"""
    try:
        tickers = portfolio_service.get_category_tickers(category_name)
        if not tickers:
            raise HTTPException(status_code=404, detail=f"Category {category_name} not found")
        return {"category": category_name, "tickers": tickers}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tickers for {category_name}: {str(e)}")

@app.get("/watchlist")
async def get_watchlist(min_score: float = 70.0) -> dict:
    """Generate watchlist of potential portfolio additions"""
    try:
        # Use the default portfolio for analysis
        watchlist = portfolio_service.generate_watchlist(DEFAULT_PORTFOLIO, min_score)
        return watchlist
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating watchlist: {str(e)}")

# ========================================
# CATEGORY MANAGEMENT ENDPOINTS
# ========================================

@app.get("/categories/management/all")
async def get_all_categories_management() -> dict:
    """Get all categories with ticker details from database"""
    try:
        category_service = CategoryService(momentum_engine=momentum_engine)  # Use shared momentum_engine with cache
        categories = category_service.get_all_categories()
        return {
            'success': True,
            'categories': categories,
            'count': len(categories)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")

@app.get("/categories/management/{category_id}")
async def get_category_details(category_id: int) -> dict:
    """Get details for a specific category"""
    try:
        category_service = CategoryService()
        category = category_service.get_category_by_id(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching category: {str(e)}")

@app.post("/categories/management/{category_id}/tickers")
async def add_ticker_to_category(category_id: int, ticker: str) -> dict:
    """Add a ticker to a category"""
    try:
        if not ticker or len(ticker) > 20:
            raise HTTPException(status_code=400, detail="Invalid ticker symbol")

        category_service = CategoryService()
        result = category_service.add_ticker_to_category(category_id, ticker.upper())

        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to add ticker'))

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding ticker: {str(e)}")

@app.delete("/categories/management/{category_id}/tickers/{ticker}")
async def remove_ticker_from_category(category_id: int, ticker: str) -> dict:
    """Remove a ticker from a category"""
    try:
        category_service = CategoryService()
        result = category_service.remove_ticker_from_category(category_id, ticker.upper())

        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to remove ticker'))

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing ticker: {str(e)}")

@app.post("/categories/management/create")
async def create_category(name: str, description: str, target_allocation_pct: float, benchmark_ticker: str) -> dict:
    """Create a new category"""
    try:
        if not name or len(name) > 100:
            raise HTTPException(status_code=400, detail="Invalid category name")

        if target_allocation_pct < 0 or target_allocation_pct > 100:
            raise HTTPException(status_code=400, detail="Target allocation must be between 0 and 100")

        category_service = CategoryService()
        result = category_service.create_category(name, description, target_allocation_pct, benchmark_ticker)

        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to create category'))

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating category: {str(e)}")

@app.put("/categories/management/{category_id}")
async def update_category(category_id: int, name: Optional[str] = None, description: Optional[str] = None,
                         target_allocation_pct: Optional[float] = None, benchmark_ticker: Optional[str] = None) -> dict:
    """Update a category"""
    try:
        category_service = CategoryService()
        result = category_service.update_category(category_id, name, description,
                                                 target_allocation_pct, benchmark_ticker)

        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to update category'))

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating category: {str(e)}")

@app.post("/watchlist/custom")
async def get_custom_watchlist(portfolio: Portfolio, min_score: float = 70.0) -> dict:
    """Generate watchlist for custom portfolio"""
    try:
        if not portfolio.holdings:
            raise HTTPException(status_code=400, detail="Portfolio cannot be empty")

        watchlist = portfolio_service.generate_watchlist(portfolio.holdings, min_score)
        return watchlist
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating custom watchlist: {str(e)}")

@app.get("/cache/status")
async def get_cache_status() -> dict:
    """Get momentum cache statistics"""
    try:
        stats = momentum_engine.get_cache_stats()
        return {
            "cache_stats": stats,
            "message": f"Cache contains {stats['valid_entries']} valid entries out of {stats['total_entries']} total"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache status: {str(e)}")

@app.post("/cache/clear")
@limiter.limit(RateLimits.BULK)
async def clear_cache(request: Request) -> dict:
    """Clear the momentum cache"""
    try:
        momentum_engine.clear_cache()
        return {"message": "Cache cleared successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

# Portfolio Comparison Endpoints

@app.post("/compare/portfolios", response_model=PortfolioComparison)
async def compare_portfolios(portfolio_a: Portfolio) -> PortfolioComparison:
    """Compare custom portfolio against model portfolio"""
    try:
        comparison = comparison_service.compare_portfolios(
            portfolio_a.holdings,
            DEFAULT_PORTFOLIO,
            portfolio_a_id="custom",
            portfolio_b_id="model"
        )

        return comparison
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing portfolios: {str(e)}")

@app.get("/compare/model-vs-custom")
async def compare_model_vs_custom(custom_portfolio: str) -> PortfolioComparison:
    """Quick comparison between model portfolio and a provided custom portfolio"""
    try:
        # Parse custom portfolio (expecting JSON string of ticker:shares mapping)
        import json
        custom_holdings = json.loads(custom_portfolio)

        comparison = comparison_service.compare_portfolios(
            custom_holdings,
            DEFAULT_PORTFOLIO,
            portfolio_a_id="custom",
            portfolio_b_id="model"
        )

        return comparison
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for custom portfolio")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in comparison: {str(e)}")

# Historical Data Endpoints

@app.get("/historical/momentum/{ticker}")
async def get_momentum_history(ticker: str, days: int = 30) -> dict:
    """Get historical momentum scores for a ticker"""
    try:
        history = momentum_engine.historical_service.get_momentum_history(ticker.upper(), days)

        if not history:
            return {
                "ticker": ticker.upper(),
                "history": [],
                "trend": "neutral",
                "current_score": 0,
                "score_change": 0,
                "message": f"No historical data available for {ticker.upper()}"
            }

        # Calculate trend
        if len(history) >= 2:
            initial_score = history[0]['composite_score']
            latest_score = history[-1]['composite_score']
            score_change = latest_score - initial_score

            if score_change > 5:
                trend = "improving"
            elif score_change < -5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "neutral"
            score_change = 0

        return {
            "ticker": ticker.upper(),
            "history": history,
            "trend": trend,
            "current_score": history[-1]['composite_score'] if history else 0,
            "score_change": score_change
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching momentum history for {ticker}: {str(e)}")

@app.get("/historical/portfolio/{portfolio_id}")
async def get_portfolio_history(portfolio_id: str = "default", days: int = 30) -> dict:
    """Get historical portfolio performance"""
    try:
        history = momentum_engine.historical_service.get_portfolio_history(portfolio_id, days)
        analytics = momentum_engine.historical_service.get_performance_analytics(portfolio_id, days)

        return {
            "portfolio_id": portfolio_id,
            "values": history['values'],
            "compositions": history['compositions'],
            "analytics": analytics
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching portfolio history: {str(e)}")

@app.get("/historical/performance/{portfolio_id}")
async def get_performance_analytics(portfolio_id: str = "default", days: int = 30) -> dict:
    """Get detailed performance analytics for a portfolio"""
    try:
        analytics = momentum_engine.historical_service.get_performance_analytics(portfolio_id, days)
        return analytics
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating performance analytics: {str(e)}")

@app.get("/historical/top-performers")
async def get_top_performers(days: int = 7) -> dict:
    """Get top performing stocks by momentum improvement"""
    try:
        performers = momentum_engine.historical_service.get_top_performers(days)
        return {
            "period_days": days,
            "performers": performers,
            "analysis_date": momentum_engine.historical_service.momentum_scores_file.stat().st_mtime if momentum_engine.historical_service.momentum_scores_file.exists() else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top performers: {str(e)}")

@app.get("/historical/chart-data/{portfolio_id}")
async def get_chart_data(portfolio_id: str = "default", days: int = 30) -> dict:
    """Get formatted data for frontend charts"""
    try:
        history = momentum_engine.historical_service.get_portfolio_history(portfolio_id, days)

        # Format for Chart.js
        chart_data: Dict[str, List[Any]] = {
            "labels": [],
            "portfolio_values": [],
            "momentum_scores": []
        }

        for entry in history['values']:
            from datetime import datetime
            # Format timestamp for display
            dt = datetime.fromisoformat(entry['timestamp'])
            chart_data["labels"].append(dt.strftime("%m/%d"))
            chart_data["portfolio_values"].append(entry['total_value'])
            chart_data["momentum_scores"].append(entry['average_momentum_score'])

        return chart_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating chart data: {str(e)}")

@app.post("/historical/portfolio/{portfolio_id}/set-id")
async def set_portfolio_id(portfolio_id: str) -> dict:
    """Set the current portfolio ID for tracking"""
    try:
        portfolio_service._current_portfolio_id = portfolio_id
        return {"message": f"Portfolio ID set to {portfolio_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting portfolio ID: {str(e)}")

@app.post("/historical/cleanup")
async def cleanup_historical_data(days_to_keep: int = 365) -> dict:
    """Clean up old historical data"""
    try:
        momentum_engine.historical_service.cleanup_old_data(days_to_keep)
        return {"message": f"Cleaned up data older than {days_to_keep} days"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up historical data: {str(e)}")

@app.post("/historical/backfill")
async def backfill_historical_data(days_back: int = 21) -> dict:
    """Backfill historical portfolio data with daily closing prices"""
    try:
        from datetime import datetime, timedelta

        logger.info(f"Starting historical data backfill for {days_back} days", extra={'days_back': days_back})

        # Get trading dates (weekdays only)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back + 7)  # Add buffer for weekends

        trading_dates = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Weekdays only
                trading_dates.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)

        successful_dates = 0
        failed_dates = []

        for date_str in trading_dates:
            try:
                # Skip if we already have data for this date
                history = momentum_engine.historical_service.get_portfolio_history('default', 1)
                existing_timestamps = [entry['timestamp'][:10] for entry in history['values']]
                if date_str in existing_timestamps:
                    logger.debug(f"Skipping {date_str}: Already have data", extra={'date': date_str})
                    continue

                logger.debug(f"Processing {date_str}", extra={'date': date_str})

                # Calculate portfolio value for this historical date
                total_value = 0
                momentum_scores = []
                valid_positions = 0

                for ticker, shares in DEFAULT_PORTFOLIO.items():
                    try:
                        # Get historical price for this specific date
                        hist = price_service.get_history_by_date_range(
                            ticker,
                            start=date_str,
                            end=(datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                        )

                        if hist is not None:
                            price = float(hist['Close'].iloc[0])

                            # Calculate historical momentum score for this specific date
                            momentum_result = momentum_engine.calculate_historical_momentum_score(ticker, date_str)

                            market_value = price * shares
                            total_value += market_value
                            momentum_scores.append(momentum_result['composite_score'])
                            valid_positions += 1

                    except Exception as e:
                        logger.warning(f"Error processing {ticker} for {date_str}", extra={'ticker': ticker, 'date': date_str, 'error': str(e)})
                        continue

                if valid_positions > 0:
                    avg_momentum = sum(momentum_scores) / len(momentum_scores)

                    # Create portfolio snapshot
                    portfolio_data = {
                        'total_value': total_value,
                        'average_momentum_score': avg_momentum,
                        'number_of_positions': valid_positions
                    }

                    # Record directly to historical service
                    timestamp = f"{date_str}T16:00:00"
                    momentum_engine.historical_service._record_portfolio_value('default', timestamp, portfolio_data)

                    logger.info(f"Recorded data for {date_str}", extra={'date': date_str, 'total_value': total_value, 'avg_momentum': avg_momentum})
                    successful_dates += 1
                else:
                    failed_dates.append(date_str)
                    logger.warning(f"No valid data for {date_str}", extra={'date': date_str})

            except Exception as e:
                failed_dates.append(date_str)
                logger.error(f"Error processing {date_str}", extra={'date': date_str, 'error': str(e)}, exc_info=True)
                continue

        return {
            "message": f"Backfill completed successfully",
            "total_dates": len(trading_dates),
            "successful_dates": successful_dates,
            "failed_dates": len(failed_dates),
            "failed_date_list": failed_dates
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during backfill: {str(e)}")

# Daily Cache Management Endpoints

@app.get("/cache/daily/status")
async def get_daily_cache_status() -> dict:
    """Get daily cache status"""
    try:
        cache_stats = daily_scheduler.cache_service.get_cache_stats()
        scheduler_status = daily_scheduler.get_scheduler_status()

        return {
            "cache_stats": cache_stats,
            "scheduler_status": scheduler_status,
            "message": f"Daily cache system with {len(PORTFOLIO_TICKERS)} tickers"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting daily cache status: {str(e)}")

@app.post("/cache/daily/update")
async def update_daily_cache(force: bool = False) -> dict:
    """Manually trigger daily cache update"""
    try:
        success = daily_scheduler.run_manual_update(force=force)

        if success:
            return {
                "message": "Daily cache updated successfully",
                "forced": force,
                "tickers_cached": len(PORTFOLIO_TICKERS)
            }
        else:
            raise HTTPException(status_code=500, detail="Daily cache update failed")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating daily cache: {str(e)}")

@app.post("/cache/daily/start")
async def start_daily_scheduler() -> dict:
    """Start the daily cache scheduler"""
    try:
        daily_scheduler.start_scheduler()
        return {"message": "Daily scheduler started successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting daily scheduler: {str(e)}")

@app.post("/cache/daily/stop")
async def stop_daily_scheduler() -> dict:
    """Stop the daily cache scheduler"""
    try:
        daily_scheduler.stop_scheduler()
        return {"message": "Daily scheduler stopped successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping daily scheduler: {str(e)}")

@app.get("/cache/daily/prices/{ticker}")
async def get_cached_price(ticker: str) -> dict:
    """Get cached price for a specific ticker"""
    try:
        price = momentum_engine.historical_service.get_cached_price(ticker.upper())
        if price > 0:
            return {
                "ticker": ticker.upper(),
                "price": price,
                "cached": True,
                "date": daily_scheduler.cache_service.get_last_trading_date()
            }
        else:
            raise HTTPException(status_code=404, detail=f"No cached price found for {ticker}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cached price: {str(e)}")

@app.get("/cache/daily/momentum/{ticker}")
async def get_cached_momentum(ticker: str) -> dict:
    """Get cached momentum score for a specific ticker"""
    try:
        momentum = momentum_engine.historical_service.get_cached_momentum_score(ticker.upper())
        if momentum:
            return {
                "ticker": ticker.upper(),
                "momentum": momentum,
                "cached": True,
                "date": daily_scheduler.cache_service.get_last_trading_date()
            }
        else:
            raise HTTPException(status_code=404, detail=f"No cached momentum found for {ticker}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cached momentum: {str(e)}")

# Database Management Endpoints (PostgreSQL)

def get_db_service() -> Any:
    """Get database service"""
    if not DATABASE_AVAILABLE or db_service is None:
        raise HTTPException(status_code=503, detail="Database service not available")
    return db_service

@app.get("/database/status")
async def get_database_status() -> dict:
    """Check database connection and availability"""
    if not DATABASE_AVAILABLE:
        return {
            "available": False,
            "message": "Database dependencies not installed"
        }

    try:
        service = get_db_service()
        connection_ok = service.test_connection()
        return {
            "available": True,
            "connected": connection_ok,
            "message": "Database connection successful" if connection_ok else "Database connection failed"
        }
    except Exception as e:
        return {
            "available": True,
            "connected": False,
            "error": str(e),
            "message": "Database connection error"
        }

@app.post("/database/migrate")
@limiter.limit(RateLimits.BULK)
async def run_database_migration(request: Request) -> dict:
    """Run database migration from JSON files"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service not available")

    try:
        from .database.migration import DatabaseMigration

        # Test connection first
        if not db_config.test_connection():
            raise HTTPException(status_code=503, detail="Cannot connect to database")

        # Run migration
        migration = DatabaseMigration()
        migration.run_full_migration()

        return {
            "message": "Database migration completed successfully",
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@app.get("/database/portfolios")
async def get_user_portfolios(user_id: int = 1) -> dict:
    """Get all portfolios for a user"""
    service = get_db_service()
    try:
        portfolios = service.get_portfolios(user_id)
        return {
            "user_id": user_id,
            "portfolios": portfolios,
            "count": len(portfolios)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching portfolios: {str(e)}")

@app.get("/database/portfolio/{portfolio_id}/holdings")
async def get_portfolio_holdings_db(portfolio_id: int) -> dict:
    """Get portfolio holdings from database"""
    service = get_db_service()
    try:
        holdings = service.get_portfolio_holdings(portfolio_id)
        return {
            "portfolio_id": portfolio_id,
            "holdings": holdings,
            "position_count": len(holdings)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching holdings: {str(e)}")

@app.get("/database/portfolio/{portfolio_id}/categories")
async def get_category_analysis_db(portfolio_id: int) -> Any:
    """Get portfolio category analysis from database"""
    service = get_db_service()
    try:
        analysis = service.get_categories_analysis(portfolio_id)
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing categories: {str(e)}")

@app.get("/database/portfolio/{portfolio_id}/categories-detailed")
async def get_portfolio_by_categories_db(portfolio_id: int) -> Any:
    """Get portfolio holdings organized by categories with detailed information"""
    service = get_db_service()
    try:
        result = service.get_portfolio_by_categories(portfolio_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categorized portfolio: {str(e)}")

@app.post("/database/portfolio/{portfolio_id}/transaction")
async def add_transaction_db(portfolio_id: int, transaction_data: dict) -> Any:
    """Add a new transaction to portfolio"""
    service = get_db_service()
    try:
        # Validate required fields
        required_fields = ['ticker', 'transaction_type', 'shares', 'price_per_share']
        for field in required_fields:
            if field not in transaction_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        result = service.add_transaction(portfolio_id, transaction_data)

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding transaction: {str(e)}")

@app.get("/database/portfolio/{portfolio_id}/transactions")
async def get_transaction_history_db(portfolio_id: int, limit: int = 50) -> dict:
    """Get transaction history for portfolio"""
    service = get_db_service()
    try:
        transactions = service.get_transactions(portfolio_id, limit)
        return {
            "portfolio_id": portfolio_id,
            "transactions": transactions,
            "count": len(transactions)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")

@app.post("/database/portfolio/{portfolio_id}/snapshot")
async def record_performance_snapshot_db(portfolio_id: int) -> Any:
    """Record daily performance snapshot"""
    service = get_db_service()
    try:
        result = service.record_performance_snapshot(portfolio_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording snapshot: {str(e)}")

@app.get("/database/portfolio/{portfolio_id}/performance")
async def get_performance_history_db(portfolio_id: int, days: int = 365) -> dict:
    """Get performance history for charting"""
    service = get_db_service()
    try:
        history = service.get_performance_history(portfolio_id, days)
        return {
            "portfolio_id": portfolio_id,
            "performance_history": history,
            "days": days
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching performance: {str(e)}")

@app.post("/database/portfolio/{portfolio_id}/update-momentum")
async def update_momentum_scores_db(portfolio_id: int) -> Any:
    """Update momentum scores for all securities in portfolio"""
    service = get_db_service()
    try:
        result = service.update_momentum_scores(portfolio_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating momentum scores: {str(e)}")

@app.get("/database/portfolio/{portfolio_id}/category-targets")
async def get_portfolio_category_targets(portfolio_id: int) -> dict:
    """Get portfolio-specific category targets"""
    try:
        from .database.config import db_config
        from .models.database import PortfolioCategoryTarget, Category

        with db_config.get_session_context() as session:
            # Get portfolio-specific targets
            targets = session.query(
                PortfolioCategoryTarget.category_id,
                PortfolioCategoryTarget.target_allocation_pct,
                Category.name,
                Category.benchmark_ticker
            ).join(Category).filter(
                PortfolioCategoryTarget.portfolio_id == portfolio_id
            ).all()

            if not targets:
                # Return global defaults if no portfolio-specific targets
                categories = session.query(Category).filter_by(is_active=True).all()
                return {
                    "portfolio_id": portfolio_id,
                    "using_defaults": True,
                    "targets": [{
                        "category_id": c.id,
                        "category_name": c.name,
                        "target_allocation_pct": float(c.target_allocation_pct) if c.target_allocation_pct else 0,
                        "benchmark": c.benchmark_ticker
                    } for c in categories]
                }

            return {
                "portfolio_id": portfolio_id,
                "using_defaults": False,
                "targets": [{
                    "category_id": t[0],
                    "category_name": t[2],
                    "target_allocation_pct": float(t[1]),
                    "benchmark": t[3]
                } for t in targets]
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching targets: {str(e)}")

@app.post("/database/portfolio/{portfolio_id}/category-targets")
async def set_portfolio_category_target(portfolio_id: int, category_id: int, target_pct: float) -> dict:
    """Set or update a portfolio-specific category target"""
    try:
        from .database.config import db_config
        from .models.database import PortfolioCategoryTarget
        from datetime import datetime

        with db_config.get_session_context() as session:
            # Check if target already exists
            target = session.query(PortfolioCategoryTarget).filter_by(
                portfolio_id=portfolio_id,
                category_id=category_id
            ).first()

            if target:
                # Update existing
                target.target_allocation_pct = target_pct
                target.updated_at = datetime.now()
            else:
                # Create new
                target = PortfolioCategoryTarget(
                    portfolio_id=portfolio_id,
                    category_id=category_id,
                    target_allocation_pct=target_pct
                )
                session.add(target)

            session.commit()
            return {"success": True, "message": "Target updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating target: {str(e)}")

@app.post("/database/portfolio/{portfolio_id}/reset-targets")
async def reset_portfolio_targets(portfolio_id: int) -> dict:
    """Reset portfolio to use global category defaults"""
    try:
        from .database.config import db_config
        from .models.database import PortfolioCategoryTarget, Category

        with db_config.get_session_context() as session:
            # Delete all portfolio-specific targets
            session.query(PortfolioCategoryTarget).filter_by(
                portfolio_id=portfolio_id
            ).delete()

            # Re-populate with global defaults
            categories = session.query(Category).filter_by(is_active=True).all()
            for cat in categories:
                if cat.name != 'Uncategorized':
                    target = PortfolioCategoryTarget(
                        portfolio_id=portfolio_id,
                        category_id=cat.id,
                        target_allocation_pct=cat.target_allocation_pct
                    )
                    session.add(target)

            session.commit()
            return {"success": True, "message": "Targets reset to defaults"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting targets: {str(e)}")

# ========== Authentication & User Management Endpoints ==========

from .auth import (
    UserCredentials, UserRegistration, UserProfile, Token, TokenPair,
    create_access_token, create_refresh_token, decode_access_token, decode_refresh_token,
    get_current_user, get_current_user_id, TokenData
)
from .services.user_service import UserService
from .services.user_portfolio_service import UserPortfolioService
from .database.config import get_database_session

def get_user_service() -> UserService:
    """Get user service with database session"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    db = next(get_database_session())
    return UserService(db)

def get_user_portfolio_service() -> UserPortfolioService:
    """Get user portfolio service with database session"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    db = next(get_database_session())
    return UserPortfolioService(db)

@app.post("/auth/register", response_model=dict)
@limiter.limit(RateLimits.AUTHENTICATION)
async def register_user(request: Request, response: Response, registration: UserRegistration) -> dict:
    """Register a new user account"""
    service = get_user_service()
    try:
        user = service.create_user(registration)
        access_token = create_access_token(user.id, user.username)
        refresh_token = create_refresh_token(user.id, user.username)

        # Register the new token family for rotation tracking
        token_data = decode_refresh_token(refresh_token)
        refresh_token_tracker.register_family(token_data.family, token_data.jti, user.id)

        return {
            "message": "User registered successfully",
            "user": UserProfile(
                id=user.id,
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_active=user.is_active,
                created_at=user.created_at
            ),
            "token": TokenPair(access_token=access_token, refresh_token=refresh_token)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/auth/login", response_model=dict)
@limiter.limit(RateLimits.AUTHENTICATION)
async def login_user(request: Request, response: Response, credentials: UserCredentials) -> Any:
    """Login with username/email and password"""
    # Check account lockout before hitting the database
    is_locked, seconds_remaining = login_attempt_tracker.is_locked(credentials.username)
    if is_locked:
        return JSONResponse(
            status_code=403,
            content={
                "error": "ACCOUNT_LOCKED",
                "message": f"Account is locked due to too many failed login attempts. Try again in {seconds_remaining} seconds.",
                "retry_after_seconds": seconds_remaining
            }
        )

    service = get_user_service()
    try:
        user = service.authenticate_user(credentials.username, credentials.password)

        if not user:
            # Record failed attempt
            just_locked, lock_seconds = login_attempt_tracker.record_failed_attempt(credentials.username)
            if just_locked:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "ACCOUNT_LOCKED",
                        "message": f"Account is locked due to too many failed login attempts. Try again in {lock_seconds} seconds.",
                        "retry_after_seconds": lock_seconds
                    }
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Successful login — clear any failed attempts
        login_attempt_tracker.record_successful_login(credentials.username)

        access_token = create_access_token(user.id, user.username)
        refresh_token = create_refresh_token(user.id, user.username)

        # Register the new token family for rotation tracking
        token_data = decode_refresh_token(refresh_token)
        refresh_token_tracker.register_family(token_data.family, token_data.jti, user.id)

        return {
            "message": "Login successful",
            "user": UserProfile(
                id=user.id,
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_active=user.is_active,
                created_at=user.created_at
            ),
            "token": TokenPair(access_token=access_token, refresh_token=refresh_token)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@app.post("/auth/refresh", response_model=dict)
@limiter.limit(RateLimits.AUTHENTICATION)
async def refresh_access_token(request: Request, response: Response, body: RefreshTokenRequest) -> Any:
    """Exchange a refresh token for a new token pair (rotation)"""
    token_data = decode_refresh_token(body.refresh_token)

    # Validate token against family tracker and rotate
    valid, new_jti = refresh_token_tracker.validate_and_rotate(token_data.family, token_data.jti)
    if not valid:
        return JSONResponse(
            status_code=401,
            content={
                "error": "TOKEN_REUSE_DETECTED",
                "message": "Refresh token has been revoked. Please log in again."
            }
        )

    # Issue new token pair
    new_access_token = create_access_token(token_data.user_id, token_data.username)
    new_refresh_token = create_refresh_token(
        token_data.user_id, token_data.username,
        family=token_data.family, jti=new_jti
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@app.get("/auth/profile", response_model=UserProfile)
async def get_profile(user_data: TokenData = Depends(get_current_user)) -> UserProfile:
    """Get current user profile"""
    service = get_user_service()
    try:
        profile = service.get_user_profile(user_data.user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching profile: {str(e)}")

@app.get("/auth/stats")
async def get_user_stats(user_id: int = Depends(get_current_user_id)) -> dict:
    """Get user statistics"""
    service = get_user_service()
    try:
        stats = service.get_user_stats(user_id)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

# ========== User Portfolio Management Endpoints ==========

@app.get("/user/portfolios")
async def get_user_portfolios(user_id: int = Depends(get_current_user_id)) -> dict:
    """Get all portfolios for the authenticated user"""
    service = get_user_portfolio_service()
    try:
        portfolios = service.get_user_portfolios(user_id)
        return {
            "portfolios": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat()
                }
                for p in portfolios
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching portfolios: {str(e)}")

@app.get("/user/portfolios/summaries")
async def get_user_portfolios_with_summaries(user_id: int = Depends(get_current_user_id)) -> dict:
    """Get all portfolios with brief summaries (value, positions, returns)"""
    service = get_user_portfolio_service()
    try:
        summaries = service.get_all_portfolios_with_summaries(user_id)
        return {
            "portfolios": summaries
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching portfolio summaries: {str(e)}")

@app.post("/user/portfolios")
async def create_user_portfolio(
    name: str,
    description: Optional[str] = None,
    user_id: int = Depends(get_current_user_id)
) -> dict:
    """Create a new portfolio"""
    service = get_user_portfolio_service()
    try:
        portfolio = service.create_portfolio(user_id, name, description)
        return {
            "message": "Portfolio created successfully",
            "portfolio": {
                "id": portfolio.id,
                "name": portfolio.name,
                "description": portfolio.description,
                "created_at": portfolio.created_at.isoformat()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating portfolio: {str(e)}")

@app.get("/user/portfolios/{portfolio_id}")
async def get_portfolio_summary(
    portfolio_id: int,
    user_id: int = Depends(get_current_user_id)
) -> dict:
    """Get portfolio summary with holdings"""
    service = get_user_portfolio_service()
    try:
        summary = service.get_portfolio_summary(portfolio_id, user_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching portfolio: {str(e)}")

@app.put("/user/portfolios/{portfolio_id}")
async def update_user_portfolio(
    portfolio_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    user_id: int = Depends(get_current_user_id)
) -> dict:
    """Update portfolio details"""
    service = get_user_portfolio_service()
    try:
        portfolio = service.update_portfolio(portfolio_id, user_id, name=name, description=description)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return {
            "message": "Portfolio updated successfully",
            "portfolio": {
                "id": portfolio.id,
                "name": portfolio.name,
                "description": portfolio.description
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating portfolio: {str(e)}")

@app.delete("/user/portfolios/{portfolio_id}")
async def delete_user_portfolio(
    portfolio_id: int,
    user_id: int = Depends(get_current_user_id)
) -> dict:
    """Delete a portfolio"""
    service = get_user_portfolio_service()
    try:
        success = service.delete_portfolio(portfolio_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return {"message": "Portfolio deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting portfolio: {str(e)}")

@app.get("/user/portfolios/{portfolio_id}/holdings")
async def get_portfolio_holdings_endpoint(
    portfolio_id: int,
    user_id: int = Depends(get_current_user_id)
) -> dict:
    """Get all holdings for a portfolio"""
    service = get_user_portfolio_service()
    try:
        holdings = service.get_portfolio_holdings(portfolio_id, user_id)
        return {"holdings": holdings}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching holdings: {str(e)}")

@app.post("/user/portfolios/{portfolio_id}/holdings")
async def add_holding(
    portfolio_id: int,
    ticker: str,
    shares: float,
    average_cost_basis: Optional[float] = None,
    category_name: Optional[str] = None,
    user_id: int = Depends(get_current_user_id)
) -> dict:
    """Add or update a holding in the portfolio"""
    service = get_user_portfolio_service()
    try:
        from decimal import Decimal
        holding = service.add_or_update_holding(
            portfolio_id,
            user_id,
            ticker,
            Decimal(str(shares)),
            Decimal(str(average_cost_basis)) if average_cost_basis else None,
            category_name
        )
        return {
            "message": "Holding added successfully",
            "holding": {
                "ticker": holding.security.ticker,
                "shares": float(holding.shares)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding holding: {str(e)}")

@app.delete("/user/portfolios/{portfolio_id}/holdings/{ticker}")
async def remove_holding_endpoint(
    portfolio_id: int,
    ticker: str,
    user_id: int = Depends(get_current_user_id)
) -> dict:
    """Remove a holding from the portfolio"""
    service = get_user_portfolio_service()
    try:
        success = service.remove_holding(portfolio_id, user_id, ticker)
        if not success:
            raise HTTPException(status_code=404, detail="Holding not found")
        return {"message": "Holding removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing holding: {str(e)}")

@app.get("/user/portfolios/{portfolio_id}/transactions")
async def get_portfolio_transactions_endpoint(
    portfolio_id: int,
    limit: int = 100,
    user_id: int = Depends(get_current_user_id)
) -> dict:
    """Get transaction history for a portfolio"""
    service = get_user_portfolio_service()
    try:
        transactions = service.get_portfolio_transactions(portfolio_id, user_id, limit)
        return {"transactions": transactions}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")

@app.post("/user/portfolios/{portfolio_id}/transactions")
async def add_transaction_endpoint(
    portfolio_id: int,
    ticker: str,
    transaction_type: str,
    shares: float,
    price_per_share: float,
    transaction_date: str,
    fees: float = 0,
    notes: Optional[str] = None,
    user_id: int = Depends(get_current_user_id)
) -> dict:
    """Add a transaction to the portfolio"""
    service = get_user_portfolio_service()
    try:
        from decimal import Decimal
        from datetime import datetime
        txn_date = datetime.strptime(transaction_date, "%Y-%m-%d").date()

        transaction = service.add_transaction(
            portfolio_id,
            user_id,
            ticker,
            transaction_type,
            Decimal(str(shares)),
            Decimal(str(price_per_share)),
            txn_date,
            Decimal(str(fees)),
            notes
        )
        return {
            "message": "Transaction added successfully",
            "transaction": {
                "id": transaction.id,
                "ticker": transaction.security.ticker,
                "transaction_type": transaction.transaction_type,
                "shares": float(transaction.shares)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding transaction: {str(e)}")

@app.delete("/user/portfolios/{portfolio_id}/transactions/{transaction_id}")
async def delete_transaction_endpoint(
    portfolio_id: int,
    transaction_id: int,
    user_id: int = Depends(get_current_user_id)
) -> dict:
    """Delete a transaction from the portfolio"""
    service = get_user_portfolio_service()
    try:
        success = service.delete_transaction(portfolio_id, user_id, transaction_id)
        if success:
            return {"message": "Transaction deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Transaction not found")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting transaction: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)