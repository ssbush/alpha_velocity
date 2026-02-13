"""
Momentum API Endpoints (v1)

Endpoints for momentum scoring and analysis.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Optional
import logging

from ...services.momentum_engine import MomentumEngine
from ...models.momentum import MomentumScore
from ...models.api_responses import TopMomentumResponse
from ...validators.validators import validate_ticker, validate_limit
from ...config.rate_limit_config import limiter, RateLimits
from ...config.portfolio_config import DEFAULT_PORTFOLIO
from .error_responses import MOMENTUM_ERRORS, VALIDATION_ERRORS

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize momentum engine (will be injected via dependency in production)
momentum_engine = MomentumEngine()


@router.get("/{ticker}", response_model=MomentumScore, responses=MOMENTUM_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_momentum_score(request: Request, ticker: str):
    """
    Get momentum score for a specific ticker symbol.

    **Parameters:**
    - ticker: Stock ticker symbol (e.g., AAPL, NVDA, MSFT)

    **Returns:**
    - Momentum score with price, technical, fundamental components
    - Overall score (0-10)
    - Rating (Strong Buy, Buy, Hold, Sell, Strong Sell)

    **Rate Limit:** 100 requests/minute (public), 200 requests/minute (authenticated)

    **Errors:**
    - 400: Invalid ticker symbol (VALIDATION_ERROR)
    - 429: Rate limit exceeded (RATE_LIMIT_EXCEEDED)
    - 502: Market data unavailable (EXTERNAL_SERVICE_ERROR)
    """
    # Validate ticker (raises InvalidTickerError automatically)
    ticker = validate_ticker(ticker)

    logger.info(f"Calculating momentum score for {ticker}")

    # Calculate momentum (errors are handled by exception handlers)
    result = momentum_engine.calculate_momentum_score(ticker)

    return MomentumScore(**result)


@router.get("/top/{limit}", response_model=TopMomentumResponse, responses=VALIDATION_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_top_momentum_stocks(
    request: Request,
    limit: int,
    category: Optional[str] = None
):
    """
    Get top momentum stocks from default portfolio or specific category.
    
    **Parameters:**
    - limit: Number of stocks to return (1-100)
    - category: Optional category filter
    
    **Returns:**
    - List of top momentum stocks sorted by score
    
    **Rate Limit:** 100 requests/minute (public), 200 requests/minute (authenticated)
    """
    try:
        # Validate limit
        limit = validate_limit(limit, max_limit=100)
        
        logger.info(f"Getting top {limit} momentum stocks (category: {category})")
        
        from ...services.portfolio_service import PortfolioService
        
        portfolio_service = PortfolioService(momentum_engine)
        
        if category:
            # Get stocks from specific category
            from ...validators.validators import sanitize_string
            category = sanitize_string(category, max_length=100)
            result = portfolio_service.get_categories_analysis(category)
            
            if 'error' in result:
                raise HTTPException(status_code=404, detail=result['error'])
                
            # Sort by momentum score and return top N
            stocks = sorted(
                result['momentum_scores'],
                key=lambda x: x['momentum_score'],
                reverse=True
            )[:limit]
            
            return {
                'category': category,
                'limit': limit,
                'stocks': stocks
            }
        else:
            # Get stocks from default portfolio
            df, total_value, avg_score = portfolio_service.analyze_portfolio(DEFAULT_PORTFOLIO)
            
            # Sort by momentum score and return top N
            df_sorted = df.nlargest(limit, 'Momentum_Score')
            
            stocks = []
            for _, row in df_sorted.iterrows():
                stocks.append({
                    'ticker': row['Ticker'],
                    'momentum_score': row['Momentum_Score'],
                    'rating': row['Rating'],
                    'price': row['Price'],
                    'market_value': row['Market_Value']
                })
            
            return {
                'limit': limit,
                'total_portfolio_stocks': len(DEFAULT_PORTFOLIO),
                'stocks': stocks
            }
            
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error getting top momentum stocks", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting top stocks: {str(e)}"
        )
