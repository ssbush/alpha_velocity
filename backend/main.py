from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List

from .services.momentum_engine import MomentumEngine
from .services.portfolio_service import PortfolioService
from .services.comparison_service import ComparisonService
from .services.daily_scheduler import initialize_scheduler, get_scheduler
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
    description="AI Supply Chain Momentum Scoring Engine",
    version="1.0.0"
)

# Add CORS middleware for mobile app access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default model portfolio for demo
DEFAULT_PORTFOLIO = {
    "NVDA": 7, "AVGO": 4, "MSFT": 2, "META": 1, "NOW": 1, "AAPL": 4, "GOOGL": 4,
    "VRT": 7, "MOD": 10, "BE": 30, "UI": 3,
    "DLR": 6, "SRVR": 58, "IRM": 10, "CCI": 10,
    "EWJ": 14, "EWT": 17,
    "SHY": 13,
    "XLI": 7,
    "MP": 16
}

# Initialize services
momentum_engine = MomentumEngine()
portfolio_service = PortfolioService(momentum_engine)
comparison_service = ComparisonService(portfolio_service)

# Database services (optional, loaded on demand)
try:
    from .simple_db_service import get_database_service
    db_service = get_database_service()
    DATABASE_AVAILABLE = db_service is not None
except ImportError as e:
    print(f"Database import failed: {e}")
    DATABASE_AVAILABLE = False
    db_service = None

# Get all portfolio tickers for caching
def get_all_portfolio_tickers():
    """Get all unique tickers from default portfolio and categories"""
    all_tickers = set(DEFAULT_PORTFOLIO.keys())

    # Add category tickers
    try:
        categories = portfolio_service.get_all_categories()
        for category_info in categories.values():
            all_tickers.update(category_info['tickers'])
    except Exception as e:
        print(f"Warning: Could not load category tickers: {e}")

    return list(all_tickers)

# Initialize daily cache scheduler
PORTFOLIO_TICKERS = get_all_portfolio_tickers()
daily_scheduler = initialize_scheduler(momentum_engine, PORTFOLIO_TICKERS)

print(f"📊 AlphaVelocity initialized with {len(PORTFOLIO_TICKERS)} tickers for daily caching")
print(f"🎯 Tickers: {', '.join(sorted(PORTFOLIO_TICKERS))}")

@app.get("/")
async def root():
    """API health check"""
    return {"message": "AlphaVelocity API is running", "version": "1.0.0"}

@app.get("/momentum/{ticker}", response_model=MomentumScore)
async def get_momentum_score(ticker: str):
    """Get momentum score for a specific ticker"""
    try:
        result = momentum_engine.calculate_momentum_score(ticker.upper())
        return MomentumScore(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating momentum for {ticker}: {str(e)}")

@app.get("/portfolio/analysis")
async def analyze_portfolio(portfolio_data: Optional[str] = None):
    """Analyze portfolio holdings (uses default if none provided)"""
    try:
        # Use default portfolio if none provided
        portfolio = DEFAULT_PORTFOLIO

        df, total_value, avg_score = portfolio_service.analyze_portfolio(portfolio)

        # Convert DataFrame to list of holdings
        holdings = []
        for _, row in df.iterrows():
            holdings.append(PortfolioHolding(
                ticker=row['Ticker'],
                shares=row['Shares'],
                price=row['Price'],
                market_value=row['Market_Value'],
                portfolio_percent=row['Portfolio_%'],
                momentum_score=row['Momentum_Score'],
                rating=row['Rating'],
                price_momentum=row['Price_Momentum'],
                technical_momentum=row['Technical_Momentum']
            ))

        return PortfolioAnalysis(
            holdings=holdings,
            total_value=total_value,
            average_momentum_score=avg_score,
            number_of_positions=len(portfolio)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing portfolio: {str(e)}")

@app.post("/portfolio/analyze")
async def analyze_custom_portfolio(portfolio: Portfolio):
    """Analyze custom portfolio holdings"""
    try:
        if not portfolio.holdings:
            raise HTTPException(status_code=400, detail="Portfolio cannot be empty")

        df, total_value, avg_score = portfolio_service.analyze_portfolio(portfolio.holdings)

        # Convert DataFrame to list of holdings
        holdings = []
        for _, row in df.iterrows():
            holdings.append(PortfolioHolding(
                ticker=row['Ticker'],
                shares=row['Shares'],
                price=row['Price'],
                market_value=row['Market_Value'],
                portfolio_percent=row['Portfolio_%'],
                momentum_score=row['Momentum_Score'],
                rating=row['Rating'],
                price_momentum=row['Price_Momentum'],
                technical_momentum=row['Technical_Momentum']
            ))

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

@app.get("/categories", response_model=List[CategoryInfo])
async def get_categories():
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")

@app.get("/categories/{category_name}/analysis", response_model=CategoryAnalysis)
async def analyze_category(category_name: str):
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
async def get_top_momentum_stocks(limit: int = 10, category: Optional[str] = None):
    """Get top momentum stocks, optionally filtered by category"""
    try:
        if limit > 50:
            limit = 50  # Reasonable limit

        result = portfolio_service.get_top_momentum_stocks(category, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top momentum stocks: {str(e)}")

@app.get("/categories/{category_name}/tickers")
async def get_category_tickers(category_name: str):
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
async def get_watchlist(min_score: float = 70.0):
    """Generate watchlist of potential portfolio additions"""
    try:
        # Use the default portfolio for analysis
        watchlist = portfolio_service.generate_watchlist(DEFAULT_PORTFOLIO, min_score)
        return watchlist
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating watchlist: {str(e)}")

@app.post("/watchlist/custom")
async def get_custom_watchlist(portfolio: Portfolio, min_score: float = 70.0):
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
async def get_cache_status():
    """Get momentum cache statistics"""
    try:
        stats = momentum_engine.get_cache_stats()
        return {
            "cache_stats": stats,
            "message": f"Cache contains {stats['valid_entries']} valid entries out of {stats['total_entries']} total"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache status: {str(e)}")

@app.post("/cache/clear")
async def clear_cache():
    """Clear the momentum cache"""
    try:
        momentum_engine.clear_cache()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

# Portfolio Comparison Endpoints

@app.post("/compare/portfolios", response_model=PortfolioComparison)
async def compare_portfolios(portfolio_a: Portfolio):
    """Compare custom portfolio against model portfolio"""
    try:
        comparison = comparison_service.compare_portfolios(
            portfolio_a.holdings,
            DEFAULT_PORTFOLIO,
            portfolio_a_id="custom",
            portfolio_b_id="model"
        )

        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing portfolios: {str(e)}")

@app.get("/compare/model-vs-custom")
async def compare_model_vs_custom(custom_portfolio: str):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in comparison: {str(e)}")

# Historical Data Endpoints

@app.get("/historical/momentum/{ticker}")
async def get_momentum_history(ticker: str, days: int = 30):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching momentum history for {ticker}: {str(e)}")

@app.get("/historical/portfolio/{portfolio_id}")
async def get_portfolio_history(portfolio_id: str = "default", days: int = 30):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching portfolio history: {str(e)}")

@app.get("/historical/performance/{portfolio_id}")
async def get_performance_analytics(portfolio_id: str = "default", days: int = 30):
    """Get detailed performance analytics for a portfolio"""
    try:
        analytics = momentum_engine.historical_service.get_performance_analytics(portfolio_id, days)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating performance analytics: {str(e)}")

@app.get("/historical/top-performers")
async def get_top_performers(days: int = 7):
    """Get top performing stocks by momentum improvement"""
    try:
        performers = momentum_engine.historical_service.get_top_performers(days)
        return {
            "period_days": days,
            "performers": performers,
            "analysis_date": momentum_engine.historical_service.momentum_scores_file.stat().st_mtime if momentum_engine.historical_service.momentum_scores_file.exists() else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top performers: {str(e)}")

@app.get("/historical/chart-data/{portfolio_id}")
async def get_chart_data(portfolio_id: str = "default", days: int = 30):
    """Get formatted data for frontend charts"""
    try:
        history = momentum_engine.historical_service.get_portfolio_history(portfolio_id, days)

        # Format for Chart.js
        chart_data = {
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating chart data: {str(e)}")

@app.post("/historical/portfolio/{portfolio_id}/set-id")
async def set_portfolio_id(portfolio_id: str):
    """Set the current portfolio ID for tracking"""
    try:
        portfolio_service._current_portfolio_id = portfolio_id
        return {"message": f"Portfolio ID set to {portfolio_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting portfolio ID: {str(e)}")

@app.post("/historical/cleanup")
async def cleanup_historical_data(days_to_keep: int = 365):
    """Clean up old historical data"""
    try:
        momentum_engine.historical_service.cleanup_old_data(days_to_keep)
        return {"message": f"Cleaned up data older than {days_to_keep} days"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up historical data: {str(e)}")

@app.post("/historical/backfill")
async def backfill_historical_data(days_back: int = 21):
    """Backfill historical portfolio data with daily closing prices"""
    try:
        from datetime import datetime, timedelta
        import yfinance as yf

        print(f"🔄 Starting historical data backfill for {days_back} days...")

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
                    print(f"  ✅ {date_str}: Already have data")
                    continue

                print(f"  🔄 Processing {date_str}...")

                # Calculate portfolio value for this historical date
                total_value = 0
                momentum_scores = []
                valid_positions = 0

                for ticker, shares in DEFAULT_PORTFOLIO.items():
                    try:
                        # Get historical price for this specific date
                        stock = yf.Ticker(ticker)
                        hist = stock.history(start=date_str, end=(datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d'))

                        if not hist.empty:
                            price = float(hist['Close'].iloc[0])

                            # Calculate historical momentum score for this specific date
                            momentum_result = momentum_engine.calculate_historical_momentum_score(ticker, date_str)

                            market_value = price * shares
                            total_value += market_value
                            momentum_scores.append(momentum_result['composite_score'])
                            valid_positions += 1

                    except Exception as e:
                        print(f"    ⚠️  {ticker}: {e}")
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

                    print(f"    ✅ Recorded: ${total_value:,.2f}, momentum: {avg_momentum:.1f}")
                    successful_dates += 1
                else:
                    failed_dates.append(date_str)
                    print(f"    ❌ No valid data for {date_str}")

            except Exception as e:
                failed_dates.append(date_str)
                print(f"  ❌ Error processing {date_str}: {e}")
                continue

        return {
            "message": f"Backfill completed successfully",
            "total_dates": len(trading_dates),
            "successful_dates": successful_dates,
            "failed_dates": len(failed_dates),
            "failed_date_list": failed_dates
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during backfill: {str(e)}")

# Daily Cache Management Endpoints

@app.get("/cache/daily/status")
async def get_daily_cache_status():
    """Get daily cache status"""
    try:
        cache_stats = daily_scheduler.cache_service.get_cache_stats()
        scheduler_status = daily_scheduler.get_scheduler_status()

        return {
            "cache_stats": cache_stats,
            "scheduler_status": scheduler_status,
            "message": f"Daily cache system with {len(PORTFOLIO_TICKERS)} tickers"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting daily cache status: {str(e)}")

@app.post("/cache/daily/update")
async def update_daily_cache(force: bool = False):
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating daily cache: {str(e)}")

@app.post("/cache/daily/start")
async def start_daily_scheduler():
    """Start the daily cache scheduler"""
    try:
        daily_scheduler.start_scheduler()
        return {"message": "Daily scheduler started successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting daily scheduler: {str(e)}")

@app.post("/cache/daily/stop")
async def stop_daily_scheduler():
    """Stop the daily cache scheduler"""
    try:
        daily_scheduler.stop_scheduler()
        return {"message": "Daily scheduler stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping daily scheduler: {str(e)}")

@app.get("/cache/daily/prices/{ticker}")
async def get_cached_price(ticker: str):
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
async def get_cached_momentum(ticker: str):
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

def get_db_service():
    """Get database service"""
    if not DATABASE_AVAILABLE or db_service is None:
        raise HTTPException(status_code=503, detail="Database service not available")
    return db_service

@app.get("/database/status")
async def get_database_status():
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
async def run_database_migration():
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@app.get("/database/portfolios")
async def get_user_portfolios(user_id: int = 1):
    """Get all portfolios for a user"""
    service = get_db_service()
    try:
        portfolios = service.get_portfolios(user_id)
        return {
            "user_id": user_id,
            "portfolios": portfolios,
            "count": len(portfolios)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching portfolios: {str(e)}")

@app.get("/database/portfolio/{portfolio_id}/holdings")
async def get_portfolio_holdings_db(portfolio_id: int):
    """Get portfolio holdings from database"""
    service = get_db_service()
    try:
        holdings = service.get_portfolio_holdings(portfolio_id)
        return {
            "portfolio_id": portfolio_id,
            "holdings": holdings,
            "position_count": len(holdings)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching holdings: {str(e)}")

@app.get("/database/portfolio/{portfolio_id}/categories")
async def get_category_analysis_db(portfolio_id: int):
    """Get portfolio category analysis from database"""
    service = get_db_service()
    try:
        analysis = service.get_categories_analysis(portfolio_id)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing categories: {str(e)}")

@app.post("/database/portfolio/{portfolio_id}/transaction")
async def add_transaction_db(portfolio_id: int, transaction_data: dict):
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
async def get_transaction_history_db(portfolio_id: int, limit: int = 50):
    """Get transaction history for portfolio"""
    service = get_db_service()
    try:
        transactions = service.get_transactions(portfolio_id, limit)
        return {
            "portfolio_id": portfolio_id,
            "transactions": transactions,
            "count": len(transactions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")

@app.post("/database/portfolio/{portfolio_id}/snapshot")
async def record_performance_snapshot_db(portfolio_id: int):
    """Record daily performance snapshot"""
    service = get_db_service()
    try:
        result = service.record_performance_snapshot(portfolio_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording snapshot: {str(e)}")

@app.get("/database/portfolio/{portfolio_id}/performance")
async def get_performance_history_db(portfolio_id: int, days: int = 365):
    """Get performance history for charting"""
    service = get_db_service()
    try:
        history = service.get_performance_history(portfolio_id, days)
        return {
            "portfolio_id": portfolio_id,
            "performance_history": history,
            "days": days
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching performance: {str(e)}")

@app.post("/database/portfolio/{portfolio_id}/update-momentum")
async def update_momentum_scores_db(portfolio_id: int):
    """Update momentum scores for all securities in portfolio"""
    service = get_db_service()
    try:
        result = service.update_momentum_scores(portfolio_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating momentum scores: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)