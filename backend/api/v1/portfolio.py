"""
Portfolio API Endpoints (v1)

Endpoints for portfolio analysis and management.
"""

from fastapi import APIRouter, HTTPException, Request, Response, Depends
from typing import Optional, List
import logging

from ...services.momentum_engine import MomentumEngine
from ...services.portfolio_service import PortfolioService
from ...models.portfolio import Portfolio, PortfolioAnalysis, PortfolioHolding
from ...config.rate_limit_config import limiter, RateLimits
from ...config.portfolio_config import DEFAULT_PORTFOLIO
from .error_responses import STANDARD_ERRORS, VALIDATION_ERRORS

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
momentum_engine = MomentumEngine()
portfolio_service = PortfolioService(momentum_engine)


@router.get("/analysis", response_model=PortfolioAnalysis, responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def analyze_default_portfolio(request: Request, response: Response):
    """
    Analyze the default model portfolio.
    
    **Returns:**
    - Complete portfolio analysis with holdings
    - Total portfolio value
    - Average momentum score
    - Number of positions
    
    **Rate Limit:** 100 requests/minute (public), 200 requests/minute (authenticated)
    """
    try:
        logger.info("Analyzing default portfolio")
        df, total_value, avg_score = portfolio_service.analyze_portfolio(DEFAULT_PORTFOLIO)

        holdings = [PortfolioHolding(**h) for h in PortfolioService.dataframe_to_holdings(df)]

        return PortfolioAnalysis(
            holdings=holdings,
            total_value=total_value,
            average_momentum_score=avg_score,
            number_of_positions=len(DEFAULT_PORTFOLIO)
        )
        
    except Exception as e:
        logger.error("Error analyzing default portfolio", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing portfolio: {str(e)}"
        )


@router.post("/analyze", response_model=PortfolioAnalysis, responses=VALIDATION_ERRORS)
@limiter.limit(RateLimits.EXPENSIVE)
async def analyze_custom_portfolio(request: Request, response: Response, portfolio: Portfolio):
    """
    Analyze a custom portfolio with user-provided holdings.
    
    **Parameters:**
    - holdings: Dictionary of ticker -> shares
    
    **Returns:**
    - Complete portfolio analysis
    
    **Rate Limit:** 10 requests/minute (resource-intensive operation)
    
    **Example Request Body:**
    ```json
    {
      "holdings": {
        "AAPL": 100,
        "NVDA": 50,
        "MSFT": 75
      }
    }
    ```
    """
    try:
        if not portfolio.holdings:
            raise HTTPException(status_code=400, detail="Portfolio cannot be empty")
        
        logger.info(f"Analyzing custom portfolio with {len(portfolio.holdings)} positions")
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
        logger.error("Error analyzing custom portfolio", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing custom portfolio: {str(e)}"
        )


@router.get("/analysis/by-categories", responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def analyze_portfolio_by_categories(request: Request, response: Response):
    """
    Analyze default portfolio grouped by categories.
    
    **Returns:**
    - Portfolio holdings grouped by investment categories
    - Category allocation percentages
    - Category performance metrics
    
    **Rate Limit:** 100 requests/minute (public), 200 requests/minute (authenticated)
    """
    try:
        logger.info("Analyzing portfolio by categories")
        result = portfolio_service.get_portfolio_by_categories(DEFAULT_PORTFOLIO)
        
        return result
        
    except Exception as e:
        logger.error("Error analyzing portfolio by categories", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing portfolio by categories: {str(e)}"
        )


@router.post("/analyze/by-categories", responses=VALIDATION_ERRORS)
@limiter.limit(RateLimits.EXPENSIVE)
async def analyze_custom_portfolio_by_categories(request: Request, response: Response, portfolio: Portfolio):
    """
    Analyze custom portfolio grouped by categories.
    
    **Parameters:**
    - holdings: Dictionary of ticker -> shares
    
    **Returns:**
    - Portfolio holdings grouped by categories
    
    **Rate Limit:** 10 requests/minute (resource-intensive operation)
    """
    try:
        if not portfolio.holdings:
            raise HTTPException(status_code=400, detail="Portfolio cannot be empty")
        
        logger.info(f"Analyzing custom portfolio by categories ({len(portfolio.holdings)} positions)")
        result = portfolio_service.get_portfolio_by_categories(portfolio.holdings)
        
        return result
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error("Error analyzing custom portfolio by categories", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing custom portfolio by categories: {str(e)}"
        )
